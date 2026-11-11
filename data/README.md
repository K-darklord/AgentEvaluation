# Data

- `raw/hle/` — item sets for the study: `hle_400_new.jsonl` (the 400 items: text-only, stratified by subject category, seed 42; built by `scripts/build_hle_400_set.py`), `hle_replication_200.json` and `hle_replication_rest200.json` (the two halves used to schedule the second and third model).
- `raw/` other files — GPQA-Diamond, MMLU-Pro, MATH-500, BFCL, BBH, AIME, GSM8K, LogiQA, FAB: used in earlier phases and to distil the error vocabulary of the bank critic (`docs/ERROR_BANK_PROVENANCE.md`). No item of Humanity's Last Exam enters that vocabulary.
- `hle_repo/` — local clone of the official benchmark repository (not committed).
- `processed/` — derived task banks from the earlier pipeline.
