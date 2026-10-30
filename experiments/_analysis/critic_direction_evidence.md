# Critic-Direction Evidence — A2 (placebo) vs C3 (strong critic), flip19 slice

> Data source: `feedback_loop_{A2,C3}_flip19_{gpqa,new,phase1}_20261022` (same 2026-10-22 timestamp).
> `critic_direction` is the structured trigger emitted by the critic at each round; the A2 placebo
> emits `None` (no direction) by design, the C3 strong critic emits `{archetype_name, suspicion}`.
> `s→f` = `start_correct → final_correct`. `correct_appeared` = the gold answer appeared in ≥1 round.

## 1. Overview: all 19 tasks, A2 vs C3

| # | task_id | family | gold | A2 s→f | C3 s→f | C3 critic_direction rounds |
|---|---------|--------|------|--------|--------|----------------------------|
| 1 | aime_018 | aime | 144 | True→True | True→True | [1, 2] |
| 2 | aime_021 | aime | 24 | False→True | False→True | [1, 2, 3] |
| 3 | aime_044 | aime | 864 | True→True | True→True | [1, 2] |
| 4 | gpqa_009 | gpqa | A | True→True | True→True | [1, 2, 3, 4, 5] |
| 5 | gpqa_016 | gpqa | A | False→False | True→True | [1, 2, 3, 4] |
| 6 | gpqa_028 | gpqa | D | True→True | False→True | [1, 2, 3, 4, 5, 6] |
| 7 | gpqa_031 | gpqa | D | False→False | True→False | [1, 2, 3] |
| 8 | gpqa_048 | gpqa | C | True→True | False→True | [1, 2, 3] |
| 9 | gpqa_049 | gpqa | D | True→False | True→False | [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] |
| 10 | gpqa_095 | gpqa | B | False→False | False→False | [1, 2, 3, 4, 5] |
| 11 | gpqa_103 | gpqa | B | False→False | False→False | [1, 2] |
| 12 | gpqa_109 | gpqa | C | True→True | True→True | [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] |
| 13 | gpqa_163 | gpqa | B | False→False | False→True | [1, 2, 3, 4, 5, 6, 7] |
| 14 | gpqa_167 | gpqa | C | False→True | True→True | [1, 2] |
| 15 | math500_010 | math500 | 4 | True→False | True→True | [1, 2] |
| 16 | math500_021 | math500 | 6+9i | True→True | True→False | [1, 2] |
| 17 | math500_027 | math500 | 144 | True→True | True→False | [1, 2, 3] |
| 18 | mmlu_pro_033 | mmlu_pro | J | True→True | False→True | [1, 2, 3] |
| 19 | mmlu_pro_047 | mmlu_pro | J | True→True | True→True | [1, 2, 3, 4, 5, 6, 7] |

## 2. Round-level `critic_direction` — C3 flip cases

Flips are `start_correct=False → final_correct=True`. Rows show every round where the C3 critic
emitted a non-empty `suspicion`; the A2 placebo has no such column because it is `None` throughout.

### aime_021  (gold = 24)

| round | answer | correct | critic_direction (suspicion) |
|---|---|---|---|
| 1 | 24 | True | procedure truncation / omission :: truncated the stepwise derivation at a subsidiary containment inequality about one object's full-side conditio |
| 2 | 24 | True | procedure truncation / omission :: omitted the step of checking both the interior-distance branch and the exterior-distance branch of the area-ba |
| 3 | 24 | True | procedure truncation / omission :: derived from a centroid-slope shortcut without explicitly validating that the candidate line satisfies the equ |


### gpqa_028  (gold = D)

| round | answer | correct | critic_direction (suspicion) |
|---|---|---|---|
| 1 | D | True | constraint-blind decimation :: reduced the final product to a planar 2D connectivity map by selecting a methylation site from substitution co || procedure truncation / omission :: omitted the final complete product representation after naming several substituent positions, truncating the d |
| 2 | D | True | constraint-blind decimation :: mistaken the mono-addition product for the final condensation product, discounting additional equivalent react || procedure truncation / omission :: violated the conservation of unsaturation by assigning all residual π-bonds to exocyclic alkylidene substituen || descriptor/label conflation :: conflated the surface label of a changed token with its semantic role in context |
| 3 | Starting (S)-4-hydroxycyclohex-2-en-1-one. TBS protection -> (S)-4-OTBS-cyclo | False | constraint-blind decimation :: assigned the C2/C3 relative configuration from a face-opposite addition rule without checking whether the low- || procedure truncation / omission :: incorporated the methyl substituent into the locant set without applying the full tie-breaking rules to the co || retrieval-abort :: emitted a memorized-looking stereochemical option after the multi-step sequence rather than re-deriving each s |
| 4 | D | True | retrieval-abort :: abandoned the stepwise derivation after the initial protection step and emitted only that fragment instead of  |
| 5 | D | True | constraint-blind decimation :: assigned the 6-methyl stereodescriptor from a 2D retrosynthetic skeleton while discounting the conformational  || procedure truncation / omission :: omitted the standard kinetic-enolate regioselectivity check before assigning the substituent locant set in the |
| 6 | D | True | constraint-blind decimation :: assigned the final (2S,3R,4S,6S) stereocluster from a planar enone template by pairing the cuprate and enolate |

> solver attribution: _Before, I had not settled on a final product and left the derivation incomplete. The reviewer’s feedback pushed me to check stereochemical approach geometry and complete the locant/naming rules. Now I hold answer D, beca_

### gpqa_048  (gold = C)

| round | answer | correct | critic_direction (suspicion) |
|---|---|---|---|
| 1 | C. 6 | True | constraint-blind decimation :: counted each hydrogen in the molecular formula as a separate chemical environment while neglecting the symmetr |
| 2 | C | False | constraint-blind decimation :: mistaken the mono-addition product for the final condensation product, discounting additional equivalent react || procedure truncation / omission :: violated the conservation of unsaturation by assigning all residual π-bonds to exocyclic alkylidene substituen || retrieval-abort :: abandoned the stepwise derivation and emitted a retrieval-miss statement in response to a multi-step synthesis |
| 3 | C | True | constraint-blind decimation :: assigned a single symmetry-equivalence count from a planar 2D ring picture while discounting the conformationa || retrieval-abort :: stopped at a recalled reaction-sequence outcome and an option mismatch, then shifted to a vague uncertainty st || descriptor/label conflation :: treated the total hydrogen count (10) as if it could be the number of chemically distinct hydrogen environment |

> solver attribution: _ERROR: My previous answer counted all 10 hydrogens as chemically distinct, ignoring symmetry equivalence in the substituted cyclopentane ring.  
REASON: The reviewer’s note about the mirror plane made me re-evaluate whic_

### gpqa_163  (gold = B)

| round | answer | correct | critic_direction (suspicion) |
|---|---|---|---|
| 1 | B | True | constraint-blind decimation :: committed to the stoichiometric acid volume while disregarding the equilibrium constraint that the final hydro |
| 2 | D | False | descriptor/label conflation :: conflated the equilibrium free-acid concentration with an additional external acid aliquot, so the reported vo || procedure truncation / omission :: omitted the standard stepwise sequence of computing the strict stoichiometric acid demand for dissolution and  |
| 3 | B | True | procedure truncation / omission :: omitted the post-stoichiometric equilibrium check and presented a volume/pH pair whose pH is inconsistent with |
| 4 | D | False | procedure truncation / omission :: omitted the metal-ion hydrolysis step after the stoichiometric neutralization and reported a pH based only on  |
| 5 | B | True | procedure truncation / omission :: omitted a final consistency check tying the reported pH to the free acid remaining after the chosen acid volum || descriptor/label conflation :: conflated the added strong-acid amount with the final hydrogen-ion concentration, treating the pre-neutralizat |
| 6 | B | True | descriptor/label conflation :: conflated thermodynamic favorability with kinetic rate || constraint-blind decimation :: misaligned the constructed vector components with the corresponding radical terms prior to applying the triang || procedure truncation / omission :: violated the conservation of unsaturation by assigning all residual π-bonds to exocyclic alkylidene substituen |
| 7 | B | True | procedure truncation / omission :: omitted the dissolution-equilibrium conditioning step and instead reported a pH that corresponds to a leftover |

> solver attribution: _Previous answer was wrong because it matched the acid volume to the neutralization stoichiometry but ignored whether the resulting pH could actually keep all Fe³⁺ dissolved. I changed it because the reviewer’s feedback c_

### mmlu_pro_033  (gold = J)

| round | answer | correct | critic_direction (suspicion) |
|---|---|---|---|
| 1 | J | True | procedure truncation / omission :: omitted one or more of the listed charges or credits when reducing the itemized total to a periodic payment || descriptor/label conflation :: conflated the annual financing rate with a total add-on rate, applying the rate in a way that changes the char || format / precision non-conformance :: reported a monthly amount as a rounded option value without preserving the cents-level periodic payment from t |
| 2 | J | True | procedure truncation / omission :: computed the monthly payment from a financed balance that omitted the cash deposit or used-car allowance befor |
| 3 | J | True | procedure truncation / omission :: omitted one or more of the itemized price components, tax, deposit, allowance, or financing term before reduci || format / precision non-conformance :: emitted only a bare choice label without exposing the requested numeric monthly amount or its dollar-per-month || retrieval-abort :: abandoned the stepwise computation in favor of a single selection made from the listed choices without an expl |

> solver attribution: _(1) ERROR: The previous answer “F” omitted several factory-installed equipment charges and did not correctly convert the annual financing rate to a monthly rate for the two-year loan.  
(2) REASON: The reviewer feedback _

## 3. A2 placebo — no direction, even where the solver eventually flipped

The A2 `critic_direction` field is `None` at every round. Where A2 still flips, the solver's own
rationale says the reviewer supplied no direction (so it re-explored unaided).

### aime_021  (gold = 24)

| round | answer | correct | critic_direction | rationale (excerpt) |
|---|---|---|---|---|
| 0 | ? Wait at m=10, s_C=-12/10.05=-1.194; yes. So |s_C|1.4086; s_C∈[3,∞) for m∈[-7.8086,1.408 | False | None |  |
| 1 | 24 | True | None | BEFORE: I had not produced a clear final answer, only an inconclusive fragment of slope computations.  
WHY: The reviewer found no confident error, but the frag |
| 2 | 24 | True | None |  |
| 3 | 24 | True | None |  |

### gpqa_167  (gold = C)

| round | answer | correct | critic_direction | rationale (excerpt) |
|---|---|---|---|---|
| 0 | D | False | None |  |
| 1 | C | True | None | ERROR: The previously selected option used an incorrect covariance-matrix determinant, so the Gaussian reference entropy was evaluated with the wrong quadrature |
| 2 | D 0? But non-Gaussianity of cat should nonzero; D 0 unlikely.
Let's search memory: There is a known measure "non-Gaussianity δ[ρ] = S(ρ||τ)" where τ is Gaussian state with same first and second moments. For pure states, δ=S | False | None | BEFORE: I previously gave a single-letter answer and was confident in it.  
WHY: The reviewer found no confident error direction, so I see no basis to change my |
| 3 | C | True | None | BEFORE: In the previous round I had not produced a final answer; I was still reasoning and unsure about how to apply the relative entropy measure.  
WHY: I then |
| 4 | =  = (-α) . Now a†|-α> = e^{-|α|^2} Σ (-α)^{n+1} √(n+1)/√n!? Actually | False | None | BEFORE: I held answer choice C from the previous round.  
WHY: The reviewer found no confident error direction, so there was no reason to change my answer.  
NO |
| 5 | C | True | None | Before: I was mid-calculation and had not yet produced a clear final answer, only a fragment of the derivation.  
Why: The previous response was truncated befor |
| 6 | C | True | None |  |
| 7 | C | True | None |  |

## 4. Confounds to state before using

- **A2/C3 are separate runs**: `start_correct` differs on several tasks (e.g. gpqa_028/048, mmlu_pro_033
  are already `start_correct=True` in A2 but `False` in C3), so a raw flip-count comparison C3(5) vs A2(2)
  is **not** a clean causal contrast — it conflates sampling noise with the direction effect.
- The clean claim is **qualitative, per-round**: C3's critic emits a concrete `suspicion` tied to the
  current error and the solver cites that feedback in its change-of-answer rationale; A2 emits `None` and
  the solver states there is *no confident error direction* to act on.
- `critic_direction` is recorded as a sidecar of the freeze (structured `archetype + suspicion`), not the
  raw critic token stream; for the paper, refer to this field, not the paraphrased rationale.
