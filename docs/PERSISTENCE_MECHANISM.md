# Results analysis — Activation × Persistence under a sequential stopping rule

**Status**: final analysis (2026-11-03), all numbers from `is_correct_t3_sidecar_v2.json` (frozen) on
HLE-400; A2 / A3 / C3 trajectories; answer identity = scorer `_key`, None / truncated rounds excluded.
Reproduce: snippets in this file's history → to be folded into `scripts/persistence_analysis.py`.

## Where it goes in the paper

Section **5.2 "Why the lock works: activation × persistence"**, placed right after the main table (5.1,
H3) and before the evaluator result (5.3). It is the *mechanism* evidence (framework stage 5) that
explains all three pairwise outcomes of the main table at once — C3 > A3 (p = .018), C3 ≈ A2 (p = .21),
A2 > A3 (n.s.) — and it states the assumption under which Stage B (exclusion) can add anything.
Three tables + one figure; ~¾ page.

## 5.2.1 Setup: three arms, one statistic

All three arms produce a sequence of committed answers x₁…xₙ for a problem and lock the most frequent
one (`vote` for A3, `mode` for A2/C3). They differ only in the process that generates the sequence:

| arm | generating process | n (valid commits, mean) |
|---|---|---|
| A3 | i.i.d. draws from p(·\|q) at T = 0.7 | 7.9 |
| A2 | Markov chain, content-free feedback, early stop at 3 identical commits | 4.1 |
| C3 | Markov chain, error-guided critic, same early stop | 5.7 |

The frequency of an answer in a chain is (entry rate) × (expected sojourn). The critic acts on the
entry rate (activation); the stopping rule acts on sojourn (persistence).

## 5.2.2 Activation (entry): what the critic does

| | A2 | C3 | A3 |
|---|---|---|---|
| tasks where the correct answer is committed at least once | 154 | **191** | 190 |
| C3 vs A2 paired (only-C3 / only-A2) | 47 / 8, p < 10⁻⁴ | | |
| C3 vs A3 paired | | 20 / 25, p = .55 | |
| distinct candidates per task | 1.9 | 3.2 | 4.1 |

<!-- resolved 2026-11-07: 190 is the ceiling over A3's nine samples (the rounds its vote rule uses), last-occurrence rule; 195 was over all ten rounds. All docs now use 190. -->
The two figures are not yet reconciled (different "reachable" aggregations). A2=154 and C3=191 are
consistent across docs; do not change the A3 number here until it is reconciled against the frozen
sidecar-v2 file. -->

The critic raises the reachable set by 25 % over the content-free loop and matches 10 i.i.d. samples
with 5.7 commits. (Table A)

## 5.2.3 Persistence (sojourn): the asymmetry is the same in C3 and A3, and A2 has less of it

| | P(next commit = current \| current correct) | … \| current wrong | ratio |
|---|---|---|---|
| A3 (i.i.d.: P(next draw equals current)) | 0.54 | 0.34 | 1.6 |
| C3 | 0.55 | 0.36 | 1.5 |
| A2 | 0.79 | 0.63 | 1.25 |

Two readings. (i) The critic does **not** make correct answers stickier per step than i.i.d. sampling
does; it re-randomises every round at roughly the i.i.d. rate. (ii) A2 is stickier in absolute terms
but *less asymmetric*: neutral feedback preserves everything, so its frequency carries less
information per commit — it simply never leaves round 0 (activation 154). The informative quantity is
the ratio, not the level. (Table B)

## 5.2.4 Compounding: why C3 beats A3 with fewer commits

The early-stop rule (3 identical commits) turns the per-step ratio into a ratio of run probabilities:
P(run ≥ 3 | entered) ∝ stay², i.e. 0.55² / 0.36² = **2.3** for C3, while a fixed-size i.i.d. vote uses
the per-step asymmetry only once. The signature is in the count distribution of the correct answer on
activated tasks:

| correct answer appears … times | 1 | 2 | 3 | ≥ 4 |
|---|---|---|---|---|
| A3 — lock correct / tasks | 18 / 53 | 14 / 22 | 19 / 23 | 90 / 92 |
| C3 | 6 / 25 | 10 / 23 | **107 / 110** | 32 / 33 |
| A2 | 1 / 8 | 5 / 6 | 125 / 125 | 14 / 15 |

In A3 the correct answer is a singleton among ~8 samples on 53 tasks and the vote loses 35 of them.
In C3 the stopping rule converts persisting correct answers into terminal 3-runs on 110 tasks and wins
107. This — not a higher per-step stickiness — is the entire C3-over-A3 margin (retention 0.80 vs
0.69; Table C). It also explains `settle` (117) < `mode` (154): settle only counts completed 3-runs,
mode also wins the 2-vs-1 cases.

## 5.2.5 The two-dimensional picture (Figure)

Scatter / bar: x = coverage (tasks with correct answer present), y = retention (lock correct /
coverage). A2 (154, 0.94), A3 (190, 0.69), C3 (191, 0.80). Lock accuracy ≈ coverage × retention:
A2 145, A3 136, C3 154. C3 is best on the product, not on either axis — the critic trades
persistence for coverage, and the stopping rule recovers part of the persistence.

Note the coincidence worth stating explicitly in the text: **C3.mode = A2's activation ceiling = 154** —
the critic loop's mode locks exactly at the neutral loop's upper bound (the number of tasks where A2
ever commits the correct answer).

Sticks both ways: the strongest *wrong* answer's share is also higher in C3 (0.53) than in A3
(0.42). Persistence is a property of the process, not of correctness; the lock profits only from the
asymmetry in §5.2.3.

## 5.2.6 Consequence for Stage B (exclusion)

A weight-1 subtractive exclusion (Q-CUT) changes the lock only where frequencies tie or differ by one
(132 of 400 tasks; 21 recoverable). Its validity rests on the same assumption as the lock itself:
`count − cut` is informative only if `count` is, i.e. only if P(stay | correct) > P(stay | wrong). Where
the asymmetry is large, few tasks tie and exclusion has little to do; where it is zero, counts are
noise and so is any correction to them. Exclusion is therefore a refinement of the persistence lock,
not an alternative to it — which is why every evaluator variant tested on the frozen trajectories
(rubric_ce, threshold sweep, check-execution, pairwise) converged on mode rather than beating it:
they added no information beyond persistence.

## Numbers to carry into the text (one place)

activation 154 / 191 / 190 · paired 47/8 (p<1e-4), 20/25 (p=.55) · stay 0.79/0.63, 0.55/0.36,
0.54/0.34 · run-3 ratio 2.3 · count-3 bucket 107/110 vs A3 singleton 18/53 · retention 0.94 / 0.80 /
0.69 · lock 145 / 154 / 136 · wrong-share 0.73 / 0.53 / 0.42 · margin ≤ 1 tasks 132, recoverable 21.
