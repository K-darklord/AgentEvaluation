"""
build_capability_matrix.py
==========================
Phase 1 (probe) build-before-burn item 1: construct the cross-domain capability
matrix tensor  model x task-family x error-type, where the error-type axis is the
SHARED cross-domain failure mode (not the family-exclusive leaf labels).

Why this exists
---------------
The 19 leaf labels in build_error_taxonomy.py are operationally defined per
family, so each leaf fires in exactly one family -> the error-type axis of the
tensor is block-diagonal on family and PARAFAC/Tucker cannot extract shared
latent capability axes. This script maps each leaf to one of 6 domain-agnostic
shared classes (MIDDLE_AXES) so a single error type can occur across >=2
families, then reports whether the block-diagonality is resolved.

Shared axes = observable failure modes (NOT an a-priori L1-L4 mapping):
  computation    arithmetic/calculation error (sign/magnitude/factor/near-miss/numeric)
  reasoning      reasoning did not converge to correct conclusion (symbolic/option/non-convergent)
  knowledge      missing or wrong facts (retrieval failure / contradiction)
  instruction    output form/label not following task instruction (empty/unparseable/non-letter/multi-letter/bad-JSON)
  tool           tool/function invocation error (tool error / wrong function / wrong argument)
  completeness   correct but partial rubric coverage (coverage incomplete)

See docs/ERROR_TAXONOMY.md for the full leaf -> literature-anchor -> rule -> axis table.
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRONG_BANK = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
OUT_DIR = ROOT / "experiments" / "capability_matrix"
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
FAMILIES = ["math", "math500", "mmlu_pro", "finance", "bfcl"]

# leaf label -> shared cross-domain middle axis (see docs/ERROR_TAXONOMY.md)
CAPABILITY_DIMENSIONS = {
    "empty_or_unparseable": "instruction",
    "empty_pred": "instruction",
    "non_letter_output": "instruction",
    "json_parse_error": "instruction",
    "multiple_letters": "instruction",
    "sign_flip": "computation",
    "magnitude_error": "computation",
    "factor_error": "computation",
    "near_miss": "computation",
    "numeric_error": "computation",
    "wrong_symbolic": "reasoning",
    "wrong_option": "reasoning",
    "complete_failure": "reasoning",
    "retrieval_failure": "knowledge",
    "contradiction": "knowledge",
    "tool_error": "tool",
    "wrong_function_name": "tool",
    "wrong_argument": "tool",
    "coverage_incomplete": "completeness",
    # defensive aliases (stale stored labels)
    "qualitative_incomplete": "completeness",
}
MIDDLE_AXES = ["computation", "reasoning", "knowledge",
               "instruction", "tool", "completeness"]


def main() -> None:
    items = [json.loads(line) for line in open(WRONG_BANK)]

    dist = defaultdict(lambda: defaultdict(Counter))
    unlabeled = []
    for it in items:
        leaf = it["error_type"]
        sc = CAPABILITY_DIMENSIONS.get(leaf)
        if sc is None:
            unlabeled.append(it)
            sc = "unmapped"
        dist[it["family"]][it["model"]][sc] += 1

    class_families = defaultdict(set)
    for fam in FAMILIES:
        for model in MODELS:
            for sc in dist[fam][model]:
                class_families[sc].add(fam)

    print("=" * 80)
    print("Shared-axis capability distribution (wrong instances, family x model)")
    print("=" * 80)
    for fam in FAMILIES:
        print(f"\n[{fam}]")
        for model in MODELS:
            c = dist[fam][model]
            if not c:
                continue
            s = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
            print(f"  {model:<18} n_wrong={sum(c.values()):>3}  {{{s}}}")

    print("\n" + "=" * 80)
    print("Cross-family coverage (block-diagonality check on shared axis)")
    print("=" * 80)
    for sc in MIDDLE_AXES:
        fams = sorted(class_families.get(sc, set()))
        status = "SHARED(>=2 families)" if len(fams) >= 2 else "single-family(under-anchored)"
        print(f"  {sc:<18} families={fams} -> {status}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dist_ser = {fam: {m: dict(c) for m, c in models.items()}
                for fam, models in dist.items()}
    payload = {
        "note": "shared cross-domain middle axis; leaf->axis via CAPABILITY_DIMENSIONS "
                "(see docs/ERROR_TAXONOMY.md)",
        "capability_distribution": dist_ser,
        "class_family_coverage": {sc: sorted(class_families.get(sc, set()))
                                  for sc in MIDDLE_AXES},
        "n_unmapped": len(unlabeled),
    }
    out = OUT_DIR / "capability_distribution.json"
    with open(out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {out}")
    if unlabeled:
        print(f"[warn] {len(unlabeled)} unmapped: "
              f"{Counter(u['error_type'] for u in unlabeled)}")


if __name__ == "__main__":
    main()
