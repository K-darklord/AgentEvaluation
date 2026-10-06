"""
build_weak_critic.py
====================
Phase 1 (probe) build-before-burn item 1c: the weak critic.

The weak critic is the Layer-1 of the meta-cognitive proxy. It is a
deterministic, gold-free Naive-Bayes classifier over the fixed 19-leaf error
taxonomy:

    Layer-0 (prior):   build_error_taxonomy.py -> wrong_bank.jsonl
                       (per model x family x prompt/gold -> error_type)
    Layer-1 (critic):  this module. Input = (family, gold-free answer signals),
                       output = posterior over that family's leaves -> Top-K=3
                       error directions + probabilities -> metacognitive prompt.

Why Naive Bayes (and nothing richer): the wrong bank has only a few dozen wrong
instances per family; after splitting by model x type most cells hold 0-20 rows,
so any capacity-rich model would overfit. Laplace smoothing (alpha=1) keeps every
leaf reachable. Phase 2 (larger data) is the intended upgrade point to
logistic/RF -- see RESEARCH_PLAN Sec 5.8.

Gold-free iron rule
-------------------
The observation features are computed from `final_answer` ONLY, plus (for
finance) the number of tool calls already recorded in the wrong bank. No feature
uses `gold_answer`; cause/attention text is fixed static and never names the
correct value. The only place the gold appears is `true_error_type` in the
sample-prediction artifact, marked reference-only and NEVER fed to the agent.

Feedback tiers (ablation)
-------------------------
  A = type phrase + probability              (baseline)
  B = A + cause (one-sentence error reason)
  C = B + attention (one-sentence directional check)

Reproducibility
---------------
- Fully deterministic (no randomness, no API, no model loading).
- One command: `python3 src/build_weak_critic.py`
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_error_taxonomy import (  # noqa: E402
    LEAF_ATTENTION, LEAF_CAUSE, ONTOLOGY,
    family_of, _extract_numbers, _json_or_none,
)

# ----------------------------------------------------------------------
# Named constants (reproducibility)
# ----------------------------------------------------------------------
CRITIC_VERSION = "v1.0"
TOP_K = 3                    # number of error directions returned
ALPHA = 1.0                  # Laplace smoothing

# Leaves per family -- the SAME fixed 19-leaf partition as ONTOLOGY /
# docs/ERROR_TAXONOMY.md. Order within a family is arbitrary; never edit the
# leaf space itself.
LEAVES_BY_FAMILY = {
    "math":     ["empty_or_unparseable", "sign_flip", "magnitude_error",
                 "factor_error", "near_miss", "wrong_symbolic"],
    "math500":  ["empty_or_unparseable", "sign_flip", "magnitude_error",
                 "factor_error", "near_miss", "wrong_symbolic"],
    "mmlu_pro": ["non_letter_output", "multiple_letters", "wrong_option"],
    "finance":  ["empty_pred", "tool_error", "retrieval_failure", "contradiction",
                 "complete_failure", "numeric_error", "coverage_incomplete"],
    "bfcl":     ["json_parse_error", "wrong_function_name", "wrong_argument",
                 "empty_pred"],
}

# Natural-language type phrase per leaf, used to render feedback WITHOUT leaking
# the internal label name (see RESEARCH_PLAN Sec 5.8 "type -> phrase" rule).
LEAF_PHRASE = {
    "sign_flip":            "a sign error",
    "magnitude_error":      "a magnitude / scale error",
    "factor_error":         "an arithmetic factor slip",
    "near_miss":            "a near-miss arithmetic slip",
    "wrong_symbolic":       "a symbolic-form error",
    "empty_or_unparseable": "an unparseable or missing answer",
    "non_letter_output":    "no option letter given",
    "multiple_letters":     "multiple option letters given",
    "wrong_option":         "the wrong option selected",
    "empty_pred":           "no final answer",
    "tool_error":           "a tool-call error",
    "retrieval_failure":    "missing source evidence",
    "contradiction":        "an evidence contradiction",
    "complete_failure":     "incomplete or truncated reasoning",
    "numeric_error":        "a numeric computation error",
    "coverage_incomplete":  "partial answer coverage",
    "json_parse_error":     "invalid JSON output",
    "wrong_function_name":  "the wrong function name",
    "wrong_argument":       "a wrong argument value",
}

# Number of categories per feature (Laplace denominator V). Features are
# categorical by construction -- numerics are bucketed to 0 / 1 / 2+.
FEATURE_CARDINALITY = {
    "empty": 2,       # T / F
    "n_nums": 3,      # 0 / 1 / 2+
    "has_neg": 2,     # T / F
    "n_letters": 3,   # 0 / 1 / 2+
    "n_tool": 3,      # 0 / 1 / 2+
    "valid_json": 2,  # T / F
}


def extract_obs(family: str, final, extra: dict | None = None) -> dict[str, str]:
    """Gold-free observation vector for one answer.

    `final` is the agent's final answer string; `extra` carries already-stored
    gold-free signals (only `n_tool_calls` is consumed, for finance). Returns a
    dict feature -> categorical value used by the Naive-Bayes table.
    """
    final = "" if final is None else str(final)
    extra = extra or {}
    obs = {"empty": "T" if final.strip() == "" else "F"}
    if family in ("math", "math500"):
        nums = _extract_numbers(final)
        n = len(nums)
        obs["n_nums"] = "0" if n == 0 else ("1" if n == 1 else "2")
        obs["has_neg"] = "T" if any(x < 0 for x in nums) else "F"
    elif family == "mmlu_pro":
        n = len(set(re.findall(r"\b[A-J]\b", final.upper())))
        obs["n_letters"] = "0" if n == 0 else ("1" if n == 1 else "2")
    elif family == "finance":
        n = int(extra.get("n_tool_calls", 0) or 0)
        obs["n_tool"] = "0" if n == 0 else ("1" if n == 1 else "2")
    elif family == "bfcl":
        obs["valid_json"] = "T" if _json_or_none(final) is not None else "F"
    return obs


class WeakCritic:
    """Deterministic Naive-Bayes critic fitted on the wrong bank."""

    def __init__(self, bank: list[dict]):
        self.bank = bank
        self.counts, self.leaf_count = self._fit(bank)

    @staticmethod
    def _fit(bank):
        counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        leaf_count = defaultdict(lambda: defaultdict(int))
        for row in bank:
            fam = row["family"]
            leaf = row["error_type"]
            obs = extract_obs(fam, row.get("final_answer", ""), row.get("signals") or {})
            leaf_count[fam][leaf] += 1
            for feat, val in obs.items():
                counts[fam][leaf][feat][val] += 1
        return counts, leaf_count

    def predict(self, family: str, final, extra: dict | None = None) -> list[tuple[str, float]]:
        """Return [(leaf, probability), ...] over the family's leaves, best first."""
        leaves = LEAVES_BY_FAMILY.get(family, [])
        if not leaves:
            return []
        obs = extract_obs(family, final, extra)
        prior_den = sum(self.leaf_count[family].get(l, 0) for l in leaves) + ALPHA * len(leaves)
        logp_by_leaf = {}
        for leaf in leaves:
            n_leaf = self.leaf_count[family].get(leaf, 0)
            logp = math.log((n_leaf + ALPHA) / prior_den)
            for feat, val in obs.items():
                cnt = self.counts[family][leaf][feat].get(val, 0)
                v = FEATURE_CARDINALITY[feat]
                logp += math.log((cnt + ALPHA) / (n_leaf + ALPHA * v))
            logp_by_leaf[leaf] = logp
        # log-sum-exp then normalize (deterministic, avoids underflow ordering issues)
        total = sum(math.exp(v) for v in logp_by_leaf.values()) or 1.0
        probs = [(l, math.exp(v) / total) for l, v in logp_by_leaf.items()]
        probs.sort(key=lambda x: (-x[1], x[0]))
        return probs

    def top_k(self, family: str, final, extra: dict | None = None, k: int = TOP_K):
        return self.predict(family, final, extra)[:k]

    @staticmethod
    def build_prompt(top_k: list[tuple[str, float]], tier: str = "A") -> str:
        """Metacognitive prompt (no mechanism confession, neutral open ending)."""
        lines = ["Re-examine your answer against the following reflections, "
                 "ordered by likelihood:", ""]
        for i, (leaf, prob) in enumerate(top_k, 1):
            lines.append(f"{i}. {LEAF_PHRASE.get(leaf, leaf)} (probability {prob:.0%})")
            if tier in ("B", "C"):
                cause = LEAF_CAUSE.get(leaf, "")
                if cause:
                    lines.append(f"   possible cause: {cause}")
            if tier == "C":
                attn = LEAF_ATTENTION.get(leaf, "")
                if attn:
                    lines.append(f"   to check: {attn}")
        lines.append("")
        lines.append("If any of these applies to your answer, revise accordingly; "
                     "otherwise keep your answer as is.")
        return "\n".join(lines)


# ----------------------------------------------------------------------
# Main: build tables from the wrong bank, run deterministic sample predictions,
# write the critic's tables + sample artifacts.
# ----------------------------------------------------------------------

def _plain(d):
    if isinstance(d, defaultdict):
        return {k: _plain(v) for k, v in d.items()}
    if isinstance(d, dict):
        return {k: _plain(v) for k, v in d.items()}
    return d


def main() -> None:
    bank_path = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
    with open(bank_path) as f:
        bank = [json.loads(line) for line in f]

    critic = WeakCritic(bank)

    # ---- deterministic sample: first wrong instance per family, in bank order ----
    samples = {}
    for row in bank:
        fam = row["family"]
        if fam in ("math", "math500", "mmlu_pro", "finance", "bfcl") and fam not in samples:
            samples[fam] = row

    out_dir = ROOT / "experiments" / "weak_critic_v1"
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_predictions = []
    print("=" * 80)
    print("Weak critic -- sample Top-3 predictions (gold-free)")
    print("=" * 80)
    for fam, row in samples.items():
        final = row.get("final_answer", "")
        extra = row.get("signals") or {}
        top3 = critic.top_k(fam, final, extra)
        pretty = ", ".join(f"{LEAF_PHRASE.get(l, l)}={p:.0%}" for l, p in top3)
        print(f"\n[{fam}] task={row['task_id']} true_type={row['error_type']}")
        print(f"  top3: {pretty}")
        entry = {
            "family": fam,
            "task_id": row["task_id"],
            "true_error_type": row["error_type"],      # reference only, never fed back
            "obs": extract_obs(fam, final, extra),
            "top3": [{"leaf": l, "probability": round(p, 6),
                      "phrase": LEAF_PHRASE.get(l, l),
                      "cause": LEAF_CAUSE.get(l, ""),
                      "attention": LEAF_ATTENTION.get(l, "")}
                     for l, p in top3],
            "prompts": {
                "A": critic.build_prompt(top3, "A"),
                "B": critic.build_prompt(top3, "B"),
                "C": critic.build_prompt(top3, "C"),
            },
        }
        sample_predictions.append(entry)

    # print one full prompt (tier C) for the first sample family
    first = samples[list(samples)[0]]
    top3 = critic.top_k(first["family"], first.get("final_answer", ""), first.get("signals") or {})
    print("\n" + "-" * 80)
    print(f"Example tier-C prompt for [{first['family']}] {first['task_id']}")
    print("-" * 80)
    print(critic.build_prompt(top3, "C"))
    print("-" * 80)

    # ---- write artifacts ----
    tables = {
        "metadata": {
            "critic_version": CRITIC_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "top_k": TOP_K,
            "alpha": ALPHA,
            "feature_cardinality": FEATURE_CARDINALITY,
            "leaves_by_family": LEAVES_BY_FAMILY,
            "type_phrase": LEAF_PHRASE,
            "leaf_cause": LEAF_CAUSE,
            "leaf_attention": LEAF_ATTENTION,
            "ontology": ONTOLOGY,
            "wrong_bank_source": str(bank_path.relative_to(ROOT)),
        },
        "feature_counts": _plain(critic.counts),
        "leaf_counts": _plain(critic.leaf_count),
    }
    tables_path = out_dir / "nb_tables.json"
    with open(tables_path, "w") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)

    samples_path = out_dir / "sample_predictions.json"
    with open(samples_path, "w") as f:
        json.dump(sample_predictions, f, indent=2, ensure_ascii=False)

    print(f"\n[written] {tables_path}")
    print(f"[written] {samples_path}")


if __name__ == "__main__":
    main()
