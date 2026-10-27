"""
egte_critic.py
==============
EGTE weak critic (exec-time feedback; frozen 2026-10-21 RSI loop).

The exec-time role: read the answer-free level-3 bank distilled for ITS OWN solver
model (``experiments/l0_distill_v1/level3_bank_{model}.json``), pick ONE archetype
direction for a (question, answer) pair, and render a FIXED natural-language hint.

Gold-free iron rules:
  - never reads gold_answer;
  - never emits a probability;
  - never emits JSON to the solver;
  - never decides keep/change (that stays in the shared scaffold in run_feedback_loop);
  - ALWAYS returns exactly one direction (no match threshold -> no "No ..." branch).

Contrast with the superseded WeakCritic (build_weak_critic.py): that returned Top-K
leaves + an estimated error probability + cause + attention. This critic is
single-direction, probability-free, and renders "possible" (suspicion), never
"confident" (2026-10-21 user decision: without a probability there is only doubt).

Internal structured output {"archetype_id", "archetype_name", "suspicion"} is returned
for the evaluator's evidence / gain statistics; only the natural-language sentence is
injected into the solver.

Retrieval: deterministic TF-IDF cosine between the (question, answer) and each entry's
answer-free text (trigger + name + definition + check_procedure). ``examples`` are
excluded from retrieval (they are de-identified and human-read-only). argmax always
selects one; ties break by (id, name). No threshold gate. Reproducible: no randomness,
no API, no model loading.

One command (smoke):
  python3 src/egte_critic.py --model glm-5.3 --question "..." --answer "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from build_weak_critic import _tokenize, _build_idf, _vect, _cos  # noqa: E402


def _retrieval_score(question: str, answer: str, entry_text: str, idf: dict, family: str) -> float:
    """Weighted question/answer similarity vs an entry's answer-free text (gold-free)."""
    qv, qn = _vect(_tokenize(family, question), idf)
    av, an = _vect(_tokenize(family, answer), idf)
    ev, en = _vect(_tokenize(family, entry_text), idf)
    sq = _cos(qv, qn, ev, en)
    sa = _cos(av, an, ev, en)
    return 0.7 * sq + 0.3 * sa


def _clean(s: str) -> str:
    """Strip trailing punctuation so the frozen template never double-punctuates."""
    return (s or "").strip().strip(" .,;:!?")


def _entry_text(e: dict) -> str:
    """Answer-free retrieval surface (examples excluded: human-read-only)."""
    return " ".join(x for x in (
        e.get("trigger", ""), e.get("name", ""),
        e.get("definition", ""), e.get("check_procedure", ""),
    ) if x)


class Level3Critic:
    """Answer-free level-3 archetype critic: single-direction, probability-free."""

    def __init__(self, entries: list[dict]):
        self.entries = entries
        self._texts = [_entry_text(e) for e in entries]
        docs = [_tokenize("gpqa", t) for t in self._texts]
        self._idf = _build_idf(docs)

    @classmethod
    def load(cls, model: str, bank_dir=None) -> "Level3Critic":
        d = Path(bank_dir) if bank_dir else (ROOT / "experiments" / "l0_distill_v1")
        path = d / f"level3_bank_{model}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data.get("entries", []))

    def ranking(self, question: str, answer: str, family: str = "gpqa"):
        """All entries ranked by text similarity, best first, with stable tie-break."""
        scored = []
        for e, txt in zip(self.entries, self._texts):
            s = _retrieval_score(question, answer, txt, self._idf, family)
            scored.append((s, e))
        scored.sort(key=lambda x: (-x[0], x[1].get("id", ""), x[1].get("name", "")))
        return scored

    def pick(self, question: str, answer: str, family: str = "gpqa"):
        """Top-1 entry + its retrieval score. ALWAYS returns an entry (never empty)."""
        ranked = self.ranking(question, answer, family)
        if not ranked:
            return (
                {"id": "none", "name": "a possible uncaught error",
                 "definition": "overlooked an answer-free check",
                 "trigger": "", "check_procedure": "re-derive from first principles"},
                0.0,
            )
        return ranked[0][1], ranked[0][0]

    def topk(self, question: str, answer: str, family: str = "gpqa",
             k: int = 3, dedup: bool = True):
        """Top-k distinct directions (dedup by archetype id) for the multi-
        direction probe. pick() remains the single-direction loop path."""
        ranked = self.ranking(question, answer, family)
        out, seen = [], set()
        for score, e in ranked:
            if dedup and e.get("id") in seen:
                continue
            seen.add(e.get("id"))
            out.append((e, score))
            if len(out) >= k:
                break
        return out

    @staticmethod
    def render(entry: dict) -> tuple[str, dict]:
        """Frozen natural-language hint + internal structured output.

        The injected sentence is the user-approved skeleton (2026-10-21): "possible"
        (suspicion), never "confident"; single direction.
        """
        name = (entry.get("name") or "").strip()
        suspicion = _clean(entry.get("definition", ""))
        check = _clean(entry.get("check_procedure", ""))
        text = (
            "A possible error direction was found for this answer:\n\n"
            f"1. {name} -- you may have {suspicion}.\n"
            f"   To check: {check}."
        )
        structured = {
            "archetype_id": entry.get("id"),
            "archetype_name": name,
            "suspicion": suspicion,
        }
        return text, structured

    @staticmethod
    def render_topk(pairs):
        """Render top-k distinct directions as a numbered possible hint."""
        if not pairs:
            return ("A possible error direction was found for this answer, "
                    "but no specific direction is available.", [])
        if len(pairs) == 1:
            text, struct = Level3Critic.render(pairs[0][0])
            return text, [struct]
        lines = ["A few possible error directions were found for this answer:"]
        structured = []
        for i, (e, _s) in enumerate(pairs, 1):
            name = (e.get("name") or "").strip()
            suspicion = _clean(e.get("definition", ""))
            check = _clean(e.get("check_procedure", ""))
            lines.append("")
            lines.append(f"{i}. {name} -- you may have {suspicion}.")
            lines.append(f"   To check: {check}.")
            structured.append({
                "archetype_id": e.get("id"),
                "archetype_name": name,
                "suspicion": suspicion,
            })
        return "\n".join(lines), structured

    def feedback(self, question: str, answer: str, family: str = "gpqa"):
        """Convenience: pick + render, returning (critic_text, structured, score)."""
        entry, score = self.pick(question, answer, family)
        text, structured = self.render(entry)
        return text, structured, score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="glm-5.3")
    ap.add_argument("--question", default="")
    ap.add_argument("--answer", default="")
    ap.add_argument("--bank-dir", default=None)
    args = ap.parse_args()

    c = Level3Critic.load(args.model, bank_dir=args.bank_dir)
    pairs = c.topk(args.question, args.answer)
    text, structured = c.render_topk(pairs)
    print("[scores] " + ", ".join(f"{s:.4f}" for _e, s in pairs))
    print(f"[structured] {json.dumps(structured, ensure_ascii=False)}")
    print("--- injected critic_text (top-3) ---")
    print(text)


if __name__ == "__main__":
    main()
