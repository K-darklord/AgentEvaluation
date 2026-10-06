"""
build_weak_critic.py
====================
Phase 1 (probe) build-before-burn item 1c: the weak critic.

The weak critic is the Layer-1 of the meta-cognitive proxy: it turns a
(question, answer) pair into a Top-K ranked error-direction distribution over
the fixed 19-leaf taxonomy, WITHOUT gold.

Architecture (rev 2, exemplar retrieval)
----------------------------------------
The prior revision used answer-shape Naive Bayes over a handful of hand-made
string features. Those features could only see FORMAT errors (empty / letter /
json / no-retrieval) and were blind to CONTENT errors (sign / magnitude /
factor / wrong-option / contradiction / numeric ...). Rev 2 replaces that with
an exemplar-retrieval classifier over the wrong bank:

    P(error | q, a)  ~  prior(error) * sum_{neighbour j} w_j * [label_j == error]

    w_j = w_q * sim_q(q, q_j) + w_a * sim_a(a, a_j)

  - sim_q : question similarity (PRIMARY). Deterministic TF-IDF cosine over a
            number-blind tokenization, so "same structure, different constants"
            questions still match (crutical for math).
  - sim_a : answer similarity (secondary refinement): numeric closeness /
            symbol for math, letter match for mmlu, token Jaccard for finance,
            JSON name+args for bfcl.
  - prior : family base-rate of each leaf (Laplace-smoothed), as before.

Gold-free iron rule: sim_q and sim_a read the question prompt + the answer only;
never gold_answer. cause/attention text stays fixed and never names the value.

Hyperparameters (defaults, to be tuned later):
  W_Q=0.7, W_A=0.3, TOP_M=10, TOP_K=3, PRIOR_SMOOTH=1.0, EVIDENCE_SMOOTH=1e-6,
  EVIDENCE_THRESHOLD=0.3 (evidence is the flag bar; error_score = base_rate x
  evidence is the number fed back to the agent).

Reproducibility: fully deterministic (no randomness, no API, no model loading).
One command: `python3 src/build_weak_critic.py`
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_error_taxonomy import (  # noqa: E402
    LEAF_ATTENTION, LEAF_CAUSE, ONTOLOGY,
    _extract_numbers, _json_or_none,
)

# ----------------------------------------------------------------------
# Named constants (reproducibility)
# ----------------------------------------------------------------------
CRITIC_VERSION = "v2.0"
TOP_K = 3          # error directions returned to the agent
TOP_M = 10         # neighbours retrieved by question similarity
W_Q = 0.7          # weight of question similarity (PRIMARY)
W_A = 0.3          # weight of answer similarity (secondary)
PRIOR_SMOOTH = 1.0     # Laplace smoothing for the leaf prior
EVIDENCE_SMOOTH = 1e-6  # tiny floor so evidence==0 falls back to the prior
EVIDENCE_THRESHOLD = 0.1   # "test positive" bar on the retrieval evidence s (the
                           # question+answer similarity vs the wrong bank). An answer
                           # whose evidence >= this bar triggers feedback; below it the
                           # critic stays silent (like a disease test turning positive
                           # only above a signal cut-off). Tune later.

# The SAME fixed 19-leaf partition (docs/ERROR_TAXONOMY.md). Never edit the
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
# the internal label name.
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


# ----------------------------------------------------------------------
# Gold-free similarity primitives
# ----------------------------------------------------------------------

def _tokenize(family: str, text) -> list[str]:
    """Number-blind tokenization for question (and generic text) similarity."""
    if not text:
        return []
    s = str(text).lower()
    if family in ("math", "math500"):
        s = re.sub(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", " NUM ", s)
    words = re.findall(r"[a-z][a-z0-9]*", s)
    if family in ("math", "math500"):
        ops = re.findall(r"[+\-*/=<>^()\[\]{}]", s)
    else:
        ops = []
    return words + ops


def _build_idf(docs: list[list[str]]) -> dict[str, float]:
    df = Counter()
    for d in docs:
        for t in set(d):
            df[t] += 1
    n = len(docs)
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def _vect(tokens: list[str], idf: dict[str, float]):
    """TF-IDF vector + its L2 norm (deterministic)."""
    c = Counter(tokens)
    v = {t: c[t] * idf.get(t, 1.0) for t in c}
    norm = math.sqrt(sum(x * x for x in v.values()))
    return v, norm


def _cos(v1, n1, v2, n2) -> float:
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    dot = sum(v1.get(t, 0.0) * v2.get(t, 0.0) for t in v1)
    return dot / (n1 * n2)


def _sim_a_math(a: str, ai: str) -> float:
    if not a and not ai:
        return 1.0
    if not a or not ai:
        return 0.0
    na = _extract_numbers(a)
    nb = _extract_numbers(ai)
    if na and nb:
        x, y = na[0], nb[0]
        if x == y:
            return 1.0
        d = abs(x - y) / max(abs(x), abs(y), 1.0)
        s = 1.0 / (1.0 + d)
        if (x > 0) == (y > 0):
            s = min(1.0, s + 0.1)
        return s
    return 1.0 if a.lower() == ai.lower() else 0.0


def _sim_a_letter(a: str, ai: str) -> float:
    la = set(re.findall(r"\b[A-J]\b", a.upper()))
    lb = set(re.findall(r"\b[A-J]\b", ai.upper()))
    if not la and not lb:
        return 1.0
    if not la or not lb:
        return 0.0
    return 1.0 if la == lb else 0.0


def _sim_a_text(a: str, ai: str) -> float:
    if not a and not ai:
        return 1.0
    if not a or not ai:
        return 0.0
    ta = set(re.findall(r"[a-z0-9]{2,}", a.lower()))
    tb = set(re.findall(r"[a-z0-9]{2,}", ai.lower()))
    if not ta and not tb:
        return 0.0
    union = len(ta | tb)
    return len(ta & tb) / union if union else 0.0


def _sim_a_bfcl(a: str, ai: str) -> float:
    pa = _json_or_none(a)
    pb = _json_or_none(ai)
    if not isinstance(pa, dict) or not isinstance(pb, dict):
        return _sim_a_text(a, ai)
    na = str(pa.get("name", "")).replace(".", "_")
    nb = str(pb.get("name", "")).replace(".", "_")
    score = 1.0 if (na == nb and na != "") else 0.2
    aa = pa.get("arguments"); ab = pb.get("arguments")
    if isinstance(aa, str):
        aa = _json_or_none(aa) or {}
    if isinstance(ab, str):
        ab = _json_or_none(ab) or {}
    if isinstance(aa, dict) and isinstance(ab, dict):
        ka, kb = set(aa), set(ab)
        union = ka | kb
        score += 0.5 * (len(ka & kb) / max(1, len(union)))
        if ka and ka == kb and all(str(aa[k]) == str(ab[k]) for k in ka):
            score = 1.0
    return min(score, 1.0)


def _sim_a(family: str, a, ai) -> float:
    a = "" if a is None else str(a).strip()
    ai = "" if ai is None else str(ai).strip()
    if family in ("math", "math500"):
        return _sim_a_math(a, ai)
    if family == "mmlu_pro":
        return _sim_a_letter(a, ai)
    if family == "finance":
        return _sim_a_text(a, ai)
    if family == "bfcl":
        return _sim_a_bfcl(a, ai)
    return 0.0


# ----------------------------------------------------------------------
# Weak critic
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Family base error rate (prevalence). In the disease-test analogy this is the
# PRIOR: how often a question of this family gets answered wrongly, independent
# of any similarity signal. Derived live from the baseline results.csv so it
# stays reproducible and never hard-coded.
# ----------------------------------------------------------------------
MODELS = ["deepseek-v4-flash", "glm-5.3", "qwen3.8-flash"]
_BASE_RATE_SPECS = [
    ("d1_baseline_20260928_201128", "math"),
    ("d1_baseline_20260928_201128", "math500"),
    ("d1_baseline_20260928_201128", "finance"),
    ("d1_baseline_20260928_201128", "bfcl"),
    ("mmlu_pro_int16_full", "mmlu_pro"),
]
_FAM_PREFIX = {"gsm8k": "math", "math500": "math500", "mmlu": "mmlu_pro",
               "fab": "finance", "bfcl": "bfcl"}


def _task_family(task_id: str) -> str | None:
    for prefix, fam in _FAM_PREFIX.items():
        if task_id.startswith(prefix):
            return fam
    return None


def _family_base_rates() -> dict[str, float]:
    """P(wrong | family) from the baseline results.csv (totals vs wrong)."""
    totals, wrongs = Counter(), Counter()
    for dname, fam in _BASE_RATE_SPECS:
        for m in MODELS:
            f = ROOT / "experiments" / dname / m / "results.csv"
            for r in csv.DictReader(open(f)):
                if _task_family(r.get("task_id", "")) != fam:
                    continue
                totals[fam] += 1
                if r["is_correct"].strip().lower() not in ("1", "true"):
                    wrongs[fam] += 1
    return {f: wrongs[f] / totals[f] for f in totals if totals[f] > 0}


class WeakCritic:
    """Exemplar-retrieval classifier: prior x retrieval-evidence, gold-free."""

    def __init__(self, bank: list[dict], base_rates: dict[str, float] | None = None):
        self.bank = bank
        self._base_rates = base_rates or {}
        self._prior: dict[str, dict[str, float]] = {}
        self._idf: dict[str, dict[str, float]] = {}
        self._exemplars: dict[str, list[dict]] = defaultdict(list)
        self._last_error = 0.0
        self._last_evidence = 0.0
        self._fit(bank)

    def _fit(self, bank):
        by_family = defaultdict(list)
        for r in bank:
            by_family[r["family"]].append(r)

        for fam, rows in by_family.items():
            leaves = LEAVES_BY_FAMILY.get(fam, [])
            if not leaves:
                continue
            # prior (Laplace)
            n = len(rows)
            counts = Counter(r["error_type"] for r in rows)
            denom = n + PRIOR_SMOOTH * len(leaves)
            self._prior[fam] = {l: (counts.get(l, 0) + PRIOR_SMOOTH) / denom
                                for l in leaves}
            # idf + document vectors
            docs = [_tokenize(fam, r.get("prompt", "")) for r in rows]
            idf = _build_idf(docs)
            self._idf[fam] = idf
            for r, tok in zip(rows, docs):
                vec, norm = _vect(tok, idf)
                self._exemplars[fam].append({
                    "task_id": r["task_id"],
                    "answer": r.get("final_answer", ""),
                    "label": r["error_type"],
                    "vec": vec, "norm": norm,
                })

    def _neighbours(self, family: str, q, exclude: set) -> list[tuple[float, dict]]:
        """Question-similarity-ranked exemplars (excluding hold-out tasks)."""
        idf = self._idf.get(family, {})
        qtok = _tokenize(family, q)
        qv, qn = _vect(qtok, idf)
        cands = []
        for ex in self._exemplars.get(family, []):
            if ex["task_id"] in exclude:
                continue
            sq = _cos(qv, qn, ex["vec"], ex["norm"])
            cands.append((sq, ex))
        cands.sort(key=lambda x: -x[0])
        return cands

    def max_q_similarity(self, family: str, q, exclude_task_ids=None) -> float:
        """Top-1 cross-question similarity; the signal used by the no-error threshold."""
        cands = self._neighbours(family, q, exclude_task_ids or set())
        return cands[0][0] if cands else 0.0

    def _signal(self, family: str, a, cands) -> tuple[float, float]:
        """Return (s, p): top-1 weighted evidence s in [0,1] and base rate p."""
        sq_top, ex_top = cands[0]
        sa_top = _sim_a(family, a, ex_top["answer"])
        s = min(1.0, max(0.0, W_Q * sq_top + W_A * sa_top))
        p = self._base_rates.get(family, 0.5)
        return s, p

    def error_score(self, family: str, q, a, exclude_task_ids=None) -> float:
        """Error probability proxy = base_rate x top-1 evidence, in [0,1].

        Only the "error" side is modelled (no explicit correct branch, per user
        decision): how often this family errs (prevalence) times how much this
        answer resembles the nearest wrong exemplar. This is the number handed
        back to the agent in the feedback; the flag/no-flag decision is a
        separate cut on the EVIDENCE (see predict).
        """
        cands = self._neighbours(family, q, exclude_task_ids or set())
        if not cands:
            return 0.0
        s, p = self._signal(family, a, cands)
        return p * s

    def _predict(self, family: str, q, a, exclude_task_ids, k):
        """Core prediction returning (top_k, evidence_s, error_score).

        Pure with respect to shared instance state: it never writes
        self._last_evidence / self._last_error, so concurrent callers
        (ThreadPoolExecutor) cannot cross-contaminate one another's signal.
        """
        leaves = LEAVES_BY_FAMILY.get(family, [])
        if not leaves:
            return [], 0.0, 0.0
        exclude = exclude_task_ids or set()
        cands = self._neighbours(family, q, exclude)
        if not cands:
            return [], 0.0, 0.0
        s, p = self._signal(family, a, cands)
        err = p * s
        if s < EVIDENCE_THRESHOLD:
            return [], s, err  # evidence below the "test positive" bar -> silent
        cands = cands[:TOP_M]

        evidence = defaultdict(float)
        for sq, ex in cands:
            sa = _sim_a(family, a, ex["answer"])
            w = W_Q * sq + W_A * sa
            if w > 0.0:
                evidence[ex["label"]] += w

        prior = self._prior.get(family, {})
        scores = {
            l: prior.get(l, 0.0) * (EVIDENCE_SMOOTH + evidence.get(l, 0.0))
            for l in leaves
        }
        total = sum(scores.values()) or 1.0
        out = [(l, scores[l] / total) for l in leaves]
        out.sort(key=lambda x: (-x[1], x[0]))
        return (out[:k] if k else out), s, err

    def predict(self, family: str, q, a, exclude_task_ids: set | None = None,
                k: int = TOP_K) -> list[tuple[str, float]]:
        """Return [(leaf, probability), ...] over the family's leaves, best first.

        Back-compat wrapper: delegates to _predict and mirrors the top-1 signal
        onto self._last_evidence / self._last_error (single-threaded helper use).
        """
        top_k, s, err = self._predict(family, q, a, exclude_task_ids, k)
        self._last_evidence = s
        self._last_error = err
        return top_k

    @staticmethod
    def build_prompt(top_k: list[tuple[str, float]], tier: str = "A",
                     error_score: float | None = None) -> str:
        if not top_k:
            return ("No confident error direction was found for this answer; "
                    "keep your answer as is.")
        lines = []
        if error_score is not None:
            lines.append(f"Estimated error probability for this answer: "
                         f"{error_score:.0%}. Decide yourself whether to revise.")
            lines.append("")
        lines.append("Re-examine your answer against the following reflections, "
                     "ordered by likelihood:")
        lines.append("")
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
# Main: leave-one-out evaluation + sample prompts + artifacts
# ----------------------------------------------------------------------

def main() -> None:
    bank_path = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
    with open(bank_path) as f:
        bank = [json.loads(line) for line in f]

    base_rates = _family_base_rates()
    critic = WeakCritic(bank, base_rates=base_rates)
    print("family base error rates (prevalence / prior):")
    for fam in ["math", "math500", "mmlu_pro", "finance", "bfcl"]:
        print(f"  {fam:<10} {base_rates.get(fam, 0.0):.1%}")
    print()

    # ---- leave-one-out (cross-question): exclude the same task_id ----
    # per_fam[fam] = [n, n_signal, top1_hit, top3_hit, prior_mode_hit]
    per_fam = defaultdict(lambda: [0, 0, 0, 0, 0])
    err_by_fam = defaultdict(list)
    evi_by_fam = defaultdict(list)
    predictions = []
    for row in bank:
        fam = row["family"]
        true = row["error_type"]
        pred = critic.predict(fam, row.get("prompt", ""), row.get("final_answer", ""),
                              exclude_task_ids={row["task_id"]}, k=None)
        err_by_fam[fam].append(round(critic._last_error, 4))
        evi_by_fam[fam].append(round(critic._last_evidence, 4))
        top3 = pred[:TOP_K]
        prior = critic._prior.get(fam, {})
        mode = max(prior, key=prior.get)
        s = per_fam[fam]
        s[0] += 1
        if pred:
            s[1] += 1
        if top3 and top3[0][0] == true:
            s[2] += 1
        if true in [l for l, _ in top3]:
            s[3] += 1
        if mode == true:
            s[4] += 1
        predictions.append({
            "task_id": row["task_id"], "family": fam, "true": true,
            "evidence": evi_by_fam[fam][-1],
            "error_score": err_by_fam[fam][-1], "no_signal": pred == [],
            "top3": [{"leaf": l, "prob": round(p, 4)} for l, p in top3],
        })

    print("=" * 80)
    print("Weak critic rev2 -- evidence-threshold flagger "
          f"EVIDENCE_THRESHOLD={EVIDENCE_THRESHOLD}")
    print("=" * 80)
    order = ["math", "math500", "mmlu_pro", "finance", "bfcl"]
    print(f"{'family':<10}{'n':>4}{'base':>7}{'no-sig':>7}{'sig':>4}"
          f"{'top1(sig)':>10}{'top3(sig)':>10}{'prior':>7}")
    for fam in order:
        if fam not in per_fam:
            continue
        n, nsig, t1, t3, pm = per_fam[fam]
        denom = nsig if nsig else 0
        t1p = t1 / denom if denom else 0.0
        t3p = t3 / denom if denom else 0.0
        print(f"{fam:<10}{n:>4}{base_rates.get(fam, 0.0):>7.1%}{n-nsig:>7}{nsig:>4}"
              f"{t1p:>10.1%}{t3p:>10.1%}{pm/n:>7.1%}")
    print("\nflag count per family across evidence thresholds:")
    for thr in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        cells = []
        for fam in order:
            vals = evi_by_fam.get(fam, [])
            cells.append(f"{fam}:{sum(1 for v in vals if v >= thr)}/{len(vals)}")
        print(f"  thr={thr:.1f}  " + "  ".join(cells))

    print("\nevidence (question+answer similarity vs wrong bank) per family:")
    for fam in order:
        vals = sorted(evi_by_fam.get(fam, []))
        if not vals:
            continue
        q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
        print(f"  {fam:<10} min={vals[0]:.3f} med={q(.5):.3f} "
              f"p90={q(.9):.3f} max={vals[-1]:.3f}")

    print("\nerror score (base_rate x evidence) distribution per family:")
    for fam in order:
        vals = sorted(err_by_fam.get(fam, []))
        if not vals:
            continue
        q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
        print(f"  {fam:<10} min={vals[0]:.3f} med={q(.5):.3f} "
              f"p90={q(.9):.3f} max={vals[-1]:.3f}")

    # ---- one sample prompt (tier C) ----
    row = bank[0]
    pred = critic.predict(row["family"], row.get("prompt", ""), row.get("final_answer", ""),
                          exclude_task_ids={row["task_id"]})
    print("\n" + "-" * 80)
    print(f"Example tier-C prompt  [{row['family']}] {row['task_id']}  (true={row['error_type']})")
    print("-" * 80)
    print(critic.build_prompt(pred, "C", error_score=critic._last_error))
    print("-" * 80)

    # ---- artifacts ----
    out_dir = ROOT / "experiments" / "weak_critic_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "critic_version": CRITIC_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hyperparameters": {"TOP_K": TOP_K, "TOP_M": TOP_M, "W_Q": W_Q,
                             "W_A": W_A, "PRIOR_SMOOTH": PRIOR_SMOOTH,
                             "EVIDENCE_SMOOTH": EVIDENCE_SMOOTH,
                             "EVIDENCE_THRESHOLD": EVIDENCE_THRESHOLD},
        "family_base_rate": base_rates,
        "leaves_by_family": LEAVES_BY_FAMILY,
        "type_phrase": LEAF_PHRASE,
        "leaf_cause": LEAF_CAUSE,
        "leaf_attention": LEAF_ATTENTION,
        "ontology": ONTOLOGY,
        "wrong_bank_source": str(bank_path.relative_to(ROOT)),
    }
    loo = {
        "leave_one_out": {fam: {"n": v[0], "n_signal": v[1], "no_signal": v[0] - v[1],
                                "top1_hits": v[2], "top3_hits": v[3],
                                "prior_mode_hits": v[4]} for fam, v in per_fam.items()},
        "predictions": predictions,
    }
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    with open(out_dir / "leave_one_out.json", "w") as f:
        json.dump(loo, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {out_dir / 'metadata.json'}")
    print(f"[written] {out_dir / 'leave_one_out.json'}")


if __name__ == "__main__":
    main()
