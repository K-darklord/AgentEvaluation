# Registration note (2026-11-18, addendum to 6f63ba5 / 6e92b77)

This note exists so that the state at registration is recorded precisely, including the fact that a
partial label file already existed. It does not change any prediction.

## What was committed, and when

| commit | content |
|---|---|
| `6f63ba5` [P2.22] | `REACH_SELECTION_DATA.md` (P1–P5), `MECHANISM_HYPOTHESIS_20261118_v2.md`, `CONTROLS_RESULTS.md` (18:50 hypotheses) |
| `6e92b77` [P2.23] | `EQUAL_TOKEN_SAMPLES_SPEC.md`, `REACH_SELECTION_DATA_TABLES.md`, `MECHANISM_HYPOTHESIS_20261118.md` (v1) |

Tag: `pre-bbeh-readout-20261118` → `6f63ba5`.

## State of the BBEH data at registration

`experiments/hle400/t3/bbeh_sidecar.json` (mtime 2026-11-18 20:35) existed. It is a **partial,
incremental artefact of runs that were still in progress**, not a finished scoring pass:

| arm | items in sidecar | mean rounds | note |
|---|---|---|---|
| A | 1040 | 1.00 | first answers |
| A2 | 1040 | 5.00 | |
| A2P | 1040 | 5.57 | |
| C2 | 1040 | 7.24 | |
| A3 | 1040 | 10.00 | nine samples |
| A2PY | **799** | 15.89 | **incomplete: 241 items missing** |

The runs were not finished when the predictions were written, and **no BBEH loop read-out
(selected / reached / conversion, by arm or by confidence stratum) had been computed or recorded**.
No such numbers exist in the repository at the time of this note.

## Ordering, stated plainly

1. 18:50 — two hypotheses (H-ability / H-state) written in `CONTROLS_RESULTS.md`; at that point the
   loop data existed but had not been scored.
2. 20:35 — the partial sidecar above appears (scoring of completed items, run incrementally).
3. 21:46 / 21:56 — five predictions P1–P5 written.
4. **No read-out yet.** The predictions therefore postdate the partial labels by about 70 minutes, and
   predate any read-out.

Consequence for the audit: P1–P5 are **not** blind to partial labels. They are blind to the read-out.
The 18:50 hypotheses are the only predictions that predate the labels; the confirmatory test rests on
them, with P1–P5 as the mechanism-level refinement.

## What must not happen now

- Do not compute any BBEH selected / reached / stratum figures from the partial sidecar.
- Do not adjust P1–P5 after seeing any number.
- When the runs finish, regenerate the sidecar in full, record its sha256 here, then run the audit
  (item counts, rounds, token alignment, shared first answer, label coverage) and only then read out.
