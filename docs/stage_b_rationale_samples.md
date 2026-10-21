# Stage B Transition Rationale — Sample Verification

> Purpose: verify the transition self-report (`rationale_mode="transition"`) across
> question types **before** re-running non-settled tasks. Settled tasks need no re-run
> (Stage B target = the non-settled remainder, PHASE2_SUMMARY item 14).

Two rationale formats are produced, keyed on the state change being described:

| Format | Prompt | Used for |
|---|---|---|
| `BEFORE` / `WHY` / `NOW` | `_TRANSITION_RATIONALE_SYSTEM_NONE` | any transition touching the `None` state (`X→None`, `None→X`, `None→None`) |
| `ERROR` / `REASON` / `FIX` | `_TRANSITION_RATIONALE_SYSTEM` | a pure answer switch `X→Y` (both non-None) |

---

## Summary of verification

| # | Question type | Task (model) | Transition kind | Format | Status |
|---|---|---|---|---|---|
| 1 | MCQ (gpqa) | gpqa_102 (glm-5.3, v2) | `None → A` | BEFORE/WHY/NOW | ✅ clean |
| 2 | Numeric (aime) | aime_043 (deepseek, v2) | `A→B` oscillation | BEFORE/WHY/NOW | ⚠️ format ok, **state mismatch** |
| 3 | Numeric (aime) | aime_035 (deepseek) | `None ↔ num` | (none) | ❌ broken |
| 4 | Function-call (bfcl) | bfcl_016 (qwen) | `None→None` | ERROR/REASON/FIX | ✅ format ok, **non-voteable** |
| 5 | glm fragment fix | gpqa_102 (glm old → new) | — | — | ✅ fixed (item 16) |

---

## Case 1 — MCQ: `None → A` (clean)

- **Task / model:** `gpqa_102` / `glm-5.3` (`transition_sample_nosettle_mcq_glm_v2`)
- **Trace:** `round 0: (no answer, "Looking")` → `round 1..3: A`
- **Transition:** `None → A`, one rationale.

```text
**BEFORE:** In the previous round I had no clear answer—my response was only
"Looking," indicating I was still reasoning and had not committed to any option.

**WHY:** The reviewer feedback flagged that no option letter was given, prompting me
to re-examine the stem and commit to a single choice rather than leaving the answer
incomplete.

**NOW:** I now hold a definitive answer of "A," selected after re-reading the question
and confirming that this option best matches the developmental fate described for the
ligand-receptor interaction.
```

✅ **Verdict: clean.** Three segments are present, the `WHY` names the reviewer signal,
and `NOW` states the newly-held answer. This is the canonical `None→X` shape.

> Note: `gpqa_102` is "non-settle at round 0" but ends with three trailing `A`s, so
> `settled_ans = A` under the formal trailing-run definition. It therefore demonstrates
> the rationale *format*, but is **not** in the strict Stage B target slice.

---

## Case 2 — Numeric: `A→B` oscillation (format ok, state mismatch)

- **Task / model:** `aime_043` / `deepseek-v4-flash` (`transition_s4_aime043_v2`)
- **Candidate answers extracted:** `45, 25, 15, 2, 5`
- **Committed sequence:** `45 → 25 → 15 → 25 → 2 → 25 → 5 → 25`

Three of the eight rationales claim "state unchanged / still hold 25" while the
extracted committed answer *changed* (see the mismatch markers below). Per
PHASE2_SUMMARY item 18, a rationale whose logic is unchanged while the letter/number
changed is an **inconsistency signal** the evaluator must surface, not silently cut.

```text
45→25
  BEFORE: I had no final answer and was still tangled in a scaled matrix setup,
          confusing row and column totals.
  WHY: I re-derived the cross-game condition properly, realizing the ten low scorers
       must total only 3 points against each high scorer, which fixed the overall totals.
  NOW: I now hold the answer 25, because that is the only player count consistent with
       the corrected point totals.

25→15  ⚠️ BEFORE says "settled on a specific numerical total", NOW says "state unchanged"
  Before: In the previous round I had settled on a specific numerical total and submitted
          it as final.
  Why: The reviewer's low error estimate and suggested scale/arithmetic checks led me to
       re-examine the derivation for any magnitude or computation slip.
  Now: After verifying the equations and final arithmetic, my state is unchanged: I still
       hold the same numerical answer.

15→25
  BEFORE: I was still reasoning and had not yet produced a final answer, as the previous
          response was truncated mid-calculation.
  WHY: I corrected the cross-game point-balance check and completed the algebra, which
       showed the total number of players must be 25.
  NOW: I hold the answer 25 because it uniquely satisfies all point-total conditions.

25→2   ⚠️ NOW says "still hold 25" while extracted answer is now "2"
  BEFORE: In the previous round I gave the answer 25 without lingering uncertainty.
  WHY: The reviewer's estimated error probability was low, and checking the relevant
       scale and arithmetic confirmed the value.
  NOW: I still hold 25, because the re-examination did not reveal a valid reason to
       revise it.

2→25
  BEFORE: I had no clear final answer—only a partial setup of notation and equations.
  WHY: I re-derived the full point-balance system and solved the resulting equations,
       confirming the unique integer total.
  NOW: I hold the answer 25, because the algebra forces exactly that number of players.

25→5   ⚠️ NOW says "hold the same answer as before" while extracted answer is now "5"
  In the previous round I had settled on the answer 25 and considered it final.
  Rechecking showed an additional aggregate solution n=16, but that solution is
  impossible because the ten lowest players' average score would exceed that of the
  other players. So I now hold the same answer as before, with the spurious
  alternative eliminated.

5→25
  BEFORE: I had not reached a clear final answer, only an unfinished check of all-tie
          cross games.
  WHY: Re-examining the point-count equations and the half-point condition showed the
       total number must satisfy a specific integer relation.
  NOW: I now hold the answer 25, because that is the unique integer making the internal
       and cross-game totals consistent.
```

⚠️ **Verdict: format is 3-part and readable, but the committed-answer extraction is
noisy.** Numeric answers (`25`) are re-stated inside prose that also contains other
digits (`n=16`, `2`, `5`), so `_family_key` / `_commit_present` picks up spurious
candidates `2`, `5`, `15`. The rationale's `NOW` self-report then disagrees with the
extracted committed answer → an inconsistency signal. This is the item-9 numeric
extraction artifact, not a rationale-prompt failure.

---

## Case 3 — Numeric: `None ↔ num` (broken)

- **Task / model:** `aime_035` / `deepseek-v4-flash` (`transition_sample_nosettle_aime`)
- **Trace:** 11 rounds; committed answers are prose fragments; most transitions carry
  `rationale = None`.

The only non-empty rationale (round 6) is the model **parroting the meta-instruction**
and re-solving the whole problem, never emitting the requested 3-part shape:

```text
We need answer in exactly three short sentences: ERROR, REASON, FIX. Need explain
previous answer "6" wrong, new answer "630" correct. Need ensure not restate question,
no answer letter. Need formulate. ...

[then a full re-derivation of the geometry, oscillating between total area 315 and 630]
```

❌ **Verdict: broken.** The model ignored the 3-part format, restated the prompt, and
re-solved the full problem in the visible rationale (the same failure mode as item 16,
but here on the *prompt-compliance* axis rather than token truncation). `deepseek` on
this numeric task does not reliably emit structured rationale.

---

## Case 4 — Function-call: `None→None` (clean format, non-voteable)

- **Task / model:** `bfcl_016` / `qwen3.8-flash` (`transition_s4_bfcl016`)
- **Trace:** JSON answer → `_family_key` returns `None` for bfcl, so every transition is
  `None→None` and **there is no voteable candidate** (empty `candidates`).

```text
ERROR: The previous answer used "x^3", which is not valid Python exponent syntax for
       the function argument.
REASON: I changed it because the reviewer indicated the argument value was wrong and
        the integrate function expects a Python expression.
FIX: The new answer uses "x**3", which correctly represents x cubed in the required
     schema.

ERROR: The previous function argument used "x**3" instead of the requested "x^3".
REASON: The reviewer flagged a wrong argument value, so the function string was aligned
        with the prompt.
FIX: The new argument uses "x^3", matching the specified curve for Simpson integration.
```

✅ format clean — but ⚠️ **bfcl is non-voteable** (`_family_key` → `None`), so it is out
of scope for the Stage B "candidates" slice. The rationale also shows an oscillation
(`x^3` ↔ `x**3`) between two forms, i.e. the same `None→None` inconsistency the format
cannot vote on.

---

## Case 5 — glm fragment fix (item 16)

| | `rationale` |
|---|---|
| old (`transition_s2_gpqa102_glm`) | `"**"` |
| new (`transition_sample_nosettle_mcq_glm_v2`) | full `BEFORE/WHY/NOW` (Case 1) |

✅ **Verdict: fixed.** Truncating the question stem in `_collect_transition_rationale` to
`_RATIONALE_QUESTION_MAX_CHARS` stops glm from re-solving the full problem in hidden CoT;
the visible rationale is now a complete 3-part sentence instead of `"**"`.

---

## Open issues to close before the re-run

1. **Numeric committed-answer extraction (Case 2).** `_family_key`/`_commit_present` for
   math/aime picks digits out of re-derivation prose, creating spurious candidates
   (`2`, `5`, `15`) and triggering false `A→B` switches. This inflates `n_transitions`
   and produces the item-18 "inconsistency signal".
2. **deepseek numeric rationale non-compliance (Case 3).** The `ERROR/REASON/FIX`
   prompt is not honored on hard numeric tasks; the model re-solves instead. Confirm the
   prompt, or verify whether this is deepseek-specific vs. general.
3. **No clean `X→None` (answer → no-answer) sample yet.** None of the current samples
   captured a committed-answer → no-answer switch with a clean 3-part rationale.
4. **bfcl non-voteable** (out of scope) — confirmed, not a bug.