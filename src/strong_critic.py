"""
strong_critic.py
================
C3 "strong" critic: an exec-time LLM critic (vs C2's deterministic TF-IDF retrieval).

Both C2 and C3 read the SAME answer-free per-model level-3 bank
(``experiments/l0_distill_v1/level3_bank_{model}.json``). The difference is SELECTION:

  C2 -> TF-IDF cosine retrieval -> top-3 possible directions (no LLM, deterministic).
  C3 -> an LLM reads (question, committed answer) and, against the answer-free
        vocabulary, REASONS which archetype(s) the answer most likely violates, then
        emits a grounded past-participle SUSPICION + a concrete gold-free CHECK.

Iron rules (identical to C2, enforced by the prompt):
  - never reads gold_answer;
  - never emits a probability / confidence score;
  - never names the correct answer / option / question-specific answer content;
  - speaks only in "possible" (suspicion), never "confident".

Reproducibility: temperature = 0, fixed model config, no sampling. The LLM call is
the SAME model family as the solver (single-model run) -- a deliberate tradeoff to
test in the C2-vs-C3 comparison, not a bug.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.agent import HuggingFaceAgent  # noqa: E402
from src.egte_critic import Level3Critic, _clean  # noqa: E402
from src import config  # noqa: E402

STRONG_CONTENT_MARGIN = int(os.environ.get("STRONG_CONTENT_MARGIN", "1024"))
# Max chars of the solver's hidden CoT fed to the strong critic so its check can be
# grounded in a specific step (lever-1: instance-specific, still gold-free).
CRITIC_REASONING_BUDGET = int(os.environ.get("CRITIC_REASONING_BUDGET", "6000"))

SYSTEM = (
    "You are the STRONG critic role of an Error-Guided Test-Time Elimination (EGTE) "
    "evaluator. At test time you inspect a solver's committed answer to a hard question "
    "and, using ONLY the answer-free wrong-execution vocabulary supplied below, identify "
    "the most likely wrong direction(s) the answer exhibits. Iron rules: never read the "
    "gold answer; never emit a probability or confidence score; never name the correct "
    "answer, option letter, or any question-specific answer content; never tell the "
    "solver what the answer IS. Speak only in \"possible\" (suspicion), never "
    "\"confident\". Return JSON only."
)


def _extract_json(content: str) -> dict | None:
    if not content:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)
    else:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            content = m.group(0)
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


class StrongCritic:
    """Exec-time LLM critic: reasons over the answer-free bank, emits possible directions.

    ``feedback`` returns ``(text, structured_list, None)`` -- the same 3-tuple shape as
    ``Level3Critic.feedback``, but ``structured_list`` holds the LLM grounding (a list of
    {id/name/suspicion} dicts) instead of a single struct.
    """

    def __init__(self, entries: list[dict], model_entry: dict):
        self.entries = entries
        self.model = model_entry
        self._weak = Level3Critic(entries)  # fallback when the LLM call/parse fails
        self._agent = HuggingFaceAgent(
            model=model_entry["model"],
            token=model_entry.get("api_key"),
            base_url=model_entry["base_url"],
            max_tokens=1024,
            temperature=0.0,
            seed=None,
            enable_thinking=model_entry.get("enable_thinking"),
            thinking_budget=model_entry.get("thinking_budget"),
            content_margin=STRONG_CONTENT_MARGIN,
        )

    @classmethod
    def load(cls, model: str, bank_dir=None) -> "StrongCritic":
        weak = Level3Critic.load(model, bank_dir=bank_dir)
        return cls(weak.entries, config.PHASE1_MODELS[model])

    def _vocab(self) -> list[dict]:
        """Dedup the bank to one answer-free archetype entry each (by id)."""
        seen: dict[str, dict] = {}
        for e in self.entries:
            seen.setdefault(e.get("id"), e)
        return list(seen.values())

    def _build_user(self, question: str, answer: str, reasoning: str = "") -> str:
        lines = [
            "Question:",
            question,
            "",
            "The model's committed answer:",
            answer,
        ]
        if reasoning:
            tail = reasoning[-CRITIC_REASONING_BUDGET:]
            prefix = "[...] " if len(reasoning) > CRITIC_REASONING_BUDGET else ""
            lines += [
                "",
                "The model's reasoning for the answer above (tail, may be truncated):",
                prefix + tail,
            ]
        lines += [
            "",
            "Wrong-execution vocabulary (pick from THESE only; answer-free):",
        ]
        for e in self._vocab():
            name = (e.get("name") or "").strip()
            definition = _clean(e.get("definition", ""))
            check = _clean(e.get("check_procedure", ""))
            lines.append(f"- {name}: {definition}")
            lines.append(f"  to check: {check}")
        lines += [
            "",
            "Return a JSON object with exactly one key \"directions\": a list of 1 to 3 "
            "objects ranked most-likely first. Each object has three string fields:",
            "  \"id\"        : the vocabulary name you invoke, verbatim from the list above",
            "  \"suspicion\" : a past-participle clause (no leading 'the answer', no 'you "
            "may have') grounded in THIS answer's specific shortcoming, still answer-free",
            "  \"check\"     : a concrete gold-free self-check the solver can run to catch "
            "it. When the reasoning above reveals a specific step, value, or assumption to "
            "re-verify, name THAT step directly (still never revealing any correct answer)",
            "Do not re-derive or re-solve the question. Output ONLY the JSON object.",
        ]
        return "\n".join(lines)

    def feedback(self, question: str, answer: str, family: str = "gpqa", reasoning: str = ""):
        """Reason over the bank and render possible directions; fall back to C2 on failure.

        ``reasoning`` is the solver's hidden CoT for the answer being critiqued; when
        present the critic grounds its ``check`` in a specific step (still gold-free).
        """
        try:
            content, _reasoning, _info = self._agent._call_llm_text(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": self._build_user(question, answer, reasoning)}])
            parsed = _extract_json(content)
            directions = parsed.get("directions", []) if parsed else []
            directions = [d for d in directions if isinstance(d, dict) and d.get("suspicion")]
            if not directions:
                raise ValueError("empty directions")
        except Exception:
            pairs = self._weak.topk(question, answer, family, k=3)
            text, structured = self._weak.render_topk(pairs)
            return text, structured, None

        lines = ["A few possible error directions were inferred for this answer:"]
        structured = []
        for i, d in enumerate(directions, 1):
            name = (d.get("id") or "").strip()
            suspicion = _clean(d.get("suspicion", ""))
            check = _clean(d.get("check", ""))
            lines.append("")
            lines.append(f"{i}. {name} -- you may have {suspicion}.")
            if check:
                lines.append(f"   To check: {check}.")
            structured.append({
                "archetype_id": None,
                "archetype_name": name,
                "suspicion": suspicion,
                "check": check,
            })
        return "\n".join(lines), structured, None
