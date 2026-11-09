# HLE-400 — Mode None-bug and evaluator (`rubric_ce`) audit, 2026-11-03

> Diagnostics file. The frozen evaluator readouts now live in `EVALUATOR_RESULTS.md` (§1–§4);
> this audit documents the mode/settle bug and the `rubric_ce` diagnosis behind them.

## 1. Mode / settle None-bug — confirmed real, fix correct, effect reproduced

`_key()` returns `None` for a round with no extractable commit (truncated ramble, prose without a value). The
old offline `_mode_idx` counted `None` as a vote key, so a run of no-commit rounds could win the mode and the
"winner" was a fragment scored wrong; the old `_settle_idx` let `None == None` form a 3-streak. Both contradict
(a) the loop's own early stop, which resets the streak on a no-commit round (`run_feedback_loop.py`, INT-23b),
and (b) `_majority_vote`, which already skipped `None` for A3. The patch (`src/score_hle_arms.py`, uncommitted)
skips `None` in both functions and scores a truncated winner as wrong.

Independent re-derivation from sidecar v2 reproduces the stated deltas exactly:

| metric | old | new | tasks changed |
|---|---|---|---|
| A2.mode | 142 | **145** | hle_099, hle_283, hle_357 (None had out-voted the correct int / letter) |
| C3.mode | 145 | **154** | hle_099, 218, 242, 240, 283, 313, 316, 335, 357 |
| C3.settle | 118 | **117** | hle_335 (old settle "settled" on a None streak) |
| A2.settle, init, final, A3.vote | — | unchanged | |

C3 has more no-commit rounds (305 vs A2's 265), so the fix helps C3 more; that is a property of the arm, not
a bias of the fix. Verdict: **accept the fix and the new numbers.**

Residual, not fixed (document as limitation, uniform across arms): the identity extractor misses some
correct commits (`\[ 0 \]`, `n=4`, option text instead of letter) — 6 (A2) / 20 (A3) / 13 (C3) correct rounds
have `None` key and can never be mode candidates. Also pre-existing: mode tie → latest, vote tie → earliest.

## 2. Evaluator (`rubric_ce`) — 146/400 by my recomputation (148 reported), below C3.mode 154

Run: 252 multi-answer tasks judged; 148 single-answer tasks inherit their only answer (69 correct). Verdict
matched to a candidate fragment → its rounds → sidecar v2 (`c3_rubric_ce.jsonl`; 4 `None` verdicts = wrong).
The 2-task gap to the reported 148 is matching detail; both are below mode.

### 2.1 Why it is lower than mode — four concrete causes

**(a) The None-bug is still inside the evaluator.** `stage_b_evaluator.py` was not patched: 37 tasks carry a
`None` candidate fragment, 83 tasks carry a truncated-round candidate, and the `all_unsure_fallback_mode`
branch uses the old mode. In the 98 fallback tasks the evaluator's verdict differs from the fixed mode in 23
and scores 29 vs mode's 34. Replacing the fallback with the fixed mode alone gives **149**. The other two
abstain-type statuses (`tie_abstain` 2, `undecided_switch` 2) are all mode-correct.

**(b) The judge's direction calls are weak on the edges that matter.** Over all 1 310 judged switch edges
(correctness of both sides from sidecar v2):

| verdict | old✓→new✗ (should CUT) | old✗→new✓ (should KEEP) | both ✓ | both ✗ |
|---|---|---|---|---|
| CUT | **39** | **20** (false CUT of the correct side) | 13 | 167 |
| KEEP | 23 (wrong keep) | 24 | 29 | 108 |
| UNSURE | 92 | **133** (correction left unrecognised) | 69 | 593 |

Direction precision on informative edges: CUT 39/59 = 66 %, KEEP 24/47 = 51 % (chance). 68 % of all edges
are UNSURE; 133 genuine corrections (wrong→correct) get no KEEP. The 14 tasks where mode is correct and the
evaluator is not are dominated by **false CUT of the transition into the correct answer** (hle_050 E→A,
hle_054 no→yes, hle_229 4.414→4.328, hle_031, hle_189, hle_217 10→11, hle_114, hle_386, hle_026 ×2).

**(c) `locked_directional` loses to mode:** 5/35 correct vs mode 9/35 on the same tasks; the tie-break
"prefer the side the confident verdicts preferred" inherits the CUT errors above (hle_189 → d3h, hle_217 → 10,
hle_114 → a truncated round-0 ramble, hle_115).

**(d) Open-form answer fragmentation.** When the correct answer is phrased differently every round
(hle_386: seven correct paraphrases, one wrong), each paraphrase has count 1, and the evaluator's tie-break
lands on the wrong one while mode's "latest" lands on a correct one. Same mechanism in hle_351, hle_115.

### 2.2 Why the pilot showed evaluator > mode

The pilot (n = 50) number 0.24 was obtained after tuning `keep` / `vote_mode` / `weight_by` on an 11-task
rescuable slice of the same 50 items (`PAPER_DRAFT` history); the +2 over mode was within that tuning. On
400 fresh items with the knobs frozen, and with mode itself corrected (+9), the advantage is gone.

### 2.3 What to do before anything enters the paper

1. Patch `stage_b_evaluator.py` to match the scorer: drop `None` and `finish_reason=="length"` rounds from
   the candidate set and from every fallback; use the fixed mode. Re-derive the locks **offline from the
   stored `per_switch` scores** (no new judge calls) and re-score. Expected ≈ 149–152.
2. If the result is still ≤ 154: the paper reports it as the pre-registered shrink condition — the
   evaluator does not add over the critic-alone mode lock on HLE-400 — and Stage B is presented as a
   negative/diagnostic result with the edge-level table above (which is itself informative: the judge's
   UNSURE rate and the false-CUT count are the measured headroom).
3. Do not re-tune `cut_bar` / knobs on HLE-400; if a tuned variant is wanted, tune on a disjoint slice.

Reproduce: `experiments/hle400/t3/c3_rubric_ce.jsonl` + `is_correct_t3_sidecar_v2.json`; edge table and the
14-task diff are regenerated by the snippet in this audit's history (`scripts/` TODO: fold into
`t3_k3_adjudicate_and_recompute.py`).

## 3. Verification of `scripts/recompute_evaluator_offline.py` (2026-11-03 13:30)

Re-ran the script and re-derived every step independently. **Reproduced:** baseline 148/400 (old verdicts,
old chain), fallback subset 34/98, corrected 149/400 on both chains, 27 changed verdicts, zero judge calls,
truncation from sidecar `s=="trunc"` with label==position. My earlier "29/98" was my own matching error
(text match on `final_answer` instead of fragment match); 34 is right. Baseline semantics are sound.

**One defect, worth +2:** two tasks whose corrected mode is *correct* end as `None`:

| task | corrected status | why `None` | fixed mode | mode correct |
|---|---|---|---|---|
| `hle_032` | `undecided_switch` (judge output unparsable, `per_switch` empty) | parse failure is treated as abstain | `(r, t)` | yes |
| `hle_283` | `tie_abstain` with **zero judged switches** (every non-None round is flanked by None rounds; "break adjacency, don't reconnect") | lock runs on 1-vs-1 candidates with no verdicts → abstain | `16` | yes |

Both contradict the method as written: the evaluator "wakes only on an answer transition" (no transition
⇒ the lock is the mode), and a judge parse failure is not a verdict (⇒ UNSURE ⇒ mode fallback). With those
two rules the corrected evaluator is **151/400**; the other three `None` tasks (`hle_164`, `hle_282`,
`hle_375`) are wrong under mode as well and do not move. The 10 tasks the script labels `locked_majority`
with zero judged switches are likewise mode fallbacks and should be labelled as such.

**Re-run with both rules in `scripts/recompute_evaluator_offline.py` — 151/400 confirmed on both chains.** Final
lock-status (n = 400): `single_answer` 151, `locked_directional` 32, `locked_majority` 100,
`all_unsure_fallback_mode` 104, `no_switch_edges_mode` 13. The 13 = 10 zero-switch `locked_majority`
tasks + 3 zero-switch `tie_abstain` tasks (`hle_282`, `hle_283`, `hle_375`). The 2 `undecided_switch`
tasks (`hle_032` empty-`per_switch`, `hle_164`) fold into `all_unsure_fallback_mode`; `tie_abstain` and
`undecided_switch` both collapse to zero, `locked_majority` drops 110 → 100.

Conclusion unchanged: evaluator 151 ≤ C3.mode 154 (−3; before the fix −6). Stage B does not add over the
critic-alone mode lock on HLE-400; report under the pre-registered shrink condition with the edge-level
table in §2.1.

## 4. Caveat found 2026-11-03 14:05 — the judge ran on half of its designed input

`stage_b_evaluator.py` (header, and `build_rubric_cut_prompt`) defines the rubric judge over **two**
inputs: the solver's transition self-report (`rationale`, collected when `rationale_mode=transition`)
and the hidden CoT. The `disconnection` dimension is *defined* as "justification break: hidden CoT →
rationale → OLD→NEW". Every HLE run — pilot n=50, HLE-150, HLE-400, all arms — was frozen with
`rationale_mode=off`; `rationale` is empty in all 2 688 C3 rounds. So on HLE the judge never had a
rationale, `disconnection` had nothing to evaluate (its AUROC 0.52 ≈ chance is consistent with that),
and `contradiction`/`error` were judged from CoT alone.

What this does and does not change:

- The Stage-B negative result must be stated as **"rubric_ce *without* the transition rationale ≤ mode"**,
  not as a verdict on the evaluator as designed. Whether the rationale adds signal is untested on HLE;
  the only prior evidence (flip19, in-family, rationale on) was qualitative.
- It does **not** change: activation (C3 193 vs A2 154, p<1e-4), retention (0.80 vs 0.94), mode numbers,
  H3 (C3.mode vs A3.vote p=0.018), or the pilot comparison (the pilot was also rationale-off; its
  evaluator gain came from knob tuning + T1 labels + the mode bug + n=50).
- Why it was off: cost (one extra solver call per answer switch) under the 2026-10-28 freeze; the
  decision assumed CoT alone sufficed. That assumption is now falsified by the AUROC numbers.

Consequence for the pending run: the next C3-type arm must set `rationale_mode=transition`
(C3-400 had ~1 310 switch edges → ~1 300 extra calls), and it is a **new arm** compared against its own
mode — the frozen C3 trajectories are not re-scorable with rationale after the fact.
