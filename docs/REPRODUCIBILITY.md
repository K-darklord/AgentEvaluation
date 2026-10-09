# Reproducibility Standard (Top-Venue Grade)

> Scope: metacognitive-agent experiments / multi-model multi-round feedback / LLM-as-a-Judge evaluation.
> Presumption: target venues are Nature Machine Intelligence / TPAMI / NeurIPS.
> Effective: from day one of model construction — never retro-fitted after the fact.

---

## 0. Mapping to this repository

The directory layout in §2.1 is the **target structure** for the Phase-1 metacognition framework. Mapping to the current repository:

| Standard path | Current repository | Status |
|---|---|---|
| `src/models/`, `src/evaluator/`, `src/experiment/`, `src/analysis/`, `src/judge/`, `src/utils/` | `agent.py`, `evaluator.py`, `runner.py`, `benchmark.py`, `config.py` (finance pipeline) | to migrate into `src/` as the Phase-1 framework matures |
| `configs/` | inline `config.py` | to be replaced by YAML configs |
| `data/raw/`, `data/processed/` | `data/fab_public.csv` | `data/` to be split |
| `results/`, `logs/` | `output/`, `experiments/` | to be reorganized per §2.1 |
| `docs/` | `docs/` (this directory) | done |

Until migration completes, the existing flat finance pipeline remains the working reference; new Phase-1 code must be written into the target `src/` structure.

---

## 1. General principles

**Three-tier definition of reproducibility (all three must hold):**

1. **Deterministic reproducibility** — same code, same data, same hardware → identical results (numeric error ≤ 1e-6).
2. **Results reproducibility** — different hardware, time, or person → the same core conclusions, with metrics within a preset tolerance band.
3. **Inferential reproducibility** — an independent researcher can run the same analysis pipeline from public materials and reach the same scientific claims.

> ⚠️ This program involves LLM sampling, so *deterministic* reproducibility is almost impossible (even with a fixed seed, API models give no guarantee). The **core target is results reproducibility**; everything deterministic (data processing, statistics, plotting) must nevertheless be deterministic.

---

## 2. Code management

### 2.1 Repository layout (mandatory)

```
project_root/
├── README.md                  # one-command reproduction guide (see §5)
├── LICENSE                    # open-source license
├── requirements.txt           # exact-pinned Python dependencies
├── environment.yml            # Conda env (optional, alternative to requirements)
├── configs/                   # all experiment configs
│   ├── baseline.yaml
│   ├── evaluator.yaml
│   ├── ablation/
│   │   ├── no_evaluator.yaml
│   │   ├── random_feedback.yaml
│   │   ├── no_voting.yaml
│   │   └── uniform_prior.yaml
│   └── judge.yaml
├── src/
│   ├── models/                # api_model.py, local_model.py
│   ├── evaluator/             # prior.py, feedback.py, voting.py
│   ├── experiment/            # run_baseline.py, run_feedback.py, run_ablation.py
│   ├── analysis/              # tensor_decomp.py, curve_fitting.py, statistics.py
│   ├── judge/                 # judge_prompt.py, judge_runner.py
│   └── utils/                 # seed.py, logger.py, io.py
├── data/
│   ├── raw/                   # raw data (with .gitkeep)
│   ├── processed/             # task_bank.json (question set + labels)
│   └── README.md              # data provenance + preprocessing
├── logs/                      # per-run logs (auto-generated)
├── results/
│   ├── raw_outputs/           # model raw outputs per round/model
│   ├── judge_scores/
│   ├── analysis/
│   └── figures/
├── scripts/
│   ├── setup_env.sh
│   ├── run_all.sh
│   └── reproduce.sh
└── docs/
    ├── EXPERIMENT_LOG.md
    └── CHANGELOG.md
```

### 2.2 Version control (mandatory)

- One commit per experiment. Commit message format:
  `[EXP] {name} | config={file} | seed={seed} | note={note}`
- One tag per milestone: `exp-{phase}-{date}` (e.g. `exp-baseline-20260926`).
- All dependencies locked to exact versions (no `>=`).
- Any non-public internal tool/data must have its acquisition method stated in README.

### 2.3 Configuration as code (mandatory)

All parameters read from config files; no hard-coding. Config fields must cover every hyperparameter that appears in the paper.

---

## 3. Randomness and seed management

### 3.1 Seed setting (mandatory)

In `src/utils/seed.py`:

```python
import random, numpy as np, torch, os

def set_seed(seed: int, deterministic: bool = True):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    if deterministic:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
```

### 3.2 Seed strategy

| Case | Strategy |
|---|---|
| Model sampling | fixed seed, and record the actual seed per run |
| Data shuffle | fixed seed (consistent ordering across runs) |
| Tensor decomposition / PCA | fixed seed |
| Ablations | same seed as the corresponding main experiment |

### 3.3 Handling LLM non-determinism

- Temperature always stated explicitly (even 0).
- Use and record the API `seed` parameter when supported (e.g. OpenAI).
- Every experiment run ≥ 3 times (different seeds); report mean and std.

### 3.4 Observed non-determinism under temperature = 0 (Phase 1, open)

**Status: tracked, root cause NOT yet determined.** Recorded 2026-10-08; to be investigated in
Phase 2. The observations below are facts; the candidate causes are hypotheses only.

**Observations (deepseek-v4-flash-0731, Aliyun Token Plan, temperature = 0, max_tokens = 8192):**

1. Two batch runs of the AIME 50-question set under identical config scored 46/50 and 42/50 —
   four items flipped between `correct` and `numeric_error` / `complete_failure`.
2. Single-item probe (`aime_033`, a boundary item whose chain-of-thought sits near the 8192 cap):
   the same fixed `seed = 42` produced `'32'` (correct, ~1977 completion tokens) on run 0, then a
   truncated chain-of-thought (`content` empty, ~8192 tokens) on runs 1 and 2. Other seeds
   (`None`, `7`) also produced truncated runs.
3. Completion-token length for the same item varies widely across identical-config calls
   (observed ~1616 / 1173 / 8192 / 5298 / 1977 / 8192 …), i.e. the hidden reasoning length is not
   pinned by `temperature = 0`.

**Candidate causes (unranked, not decided):**

- the API `seed` parameter is not wired (`HuggingFaceAgent.seed = None` by default);
- the serving endpoint does not honour `seed` / `temperature = 0` as strict greedy for the hidden
  chain-of-thought (or MoE routing carries server-side randomness);
- an intrinsic length fluctuation in reasoning-model CoT, exposed only where the CoT crosses the
  `max_tokens` cap (8192) — the boundary flip is the *visible* symptom, not necessarily the cause.

**Impact.** Single-pass accuracy numbers carry ± a few items of run-to-run noise on CoT-boundary
families (AIME / GPQA); the "reproducible under temperature = 0" claim in PHASE1_SUMMARY is too
strong and is retracted until Phase 2 settles the cause.

**Phase-2 follow-up (required):** (a) fix and record `seed` per run; (b) test whether a fixed seed
actually reproduces identical output (≥ 3 repeats of the same seed); (c) check whether qwen/glm show
the same behaviour or it is deepseek-specific; (d) decide whether to raise `REASONING_BENCH_MAX_TOKENS`
past 8192 to move CoT off the boundary.

---

## 4. Experiment configuration manifest (paper appendix)

Must be listed in full in the appendix:

**Model config** — exact name (incl. fine-tune), source (HF link + commit hash), inference engine (vLLM/TGI/transformers), quantization, temperature, top_p, max_tokens, system prompt (verbatim), user-prompt template (verbatim).

**Evaluator config** — prior construction (error distribution from round-1 baseline), Top-K value, feedback template (verbatim), voting mechanism, prior update rule.

**Experiment params** — number of task classes, questions per class, total rounds N, ablation list, independent-run count.

**LLM-as-Judge config** — judge model (name + version), judge prompt (verbatim), temperature, aggregation (e.g. 3 judges majority vote), human-spot-check ratio, human–judge agreement rate.

**Hardware** — GPU (model + count), VRAM, CPU, memory, OS, CUDA, Python.

---

## 5. One-command reproduction (README core)

```markdown
## Quick Start (5 min, minimal test)
git clone <repo_url> && cd <repo_name>
bash scripts/setup_env.sh
bash scripts/run_minimal.sh   # 1 model × 1 task class × 10 Qs × 2 rounds

## Full Reproduction (~24 h)
bash scripts/reproduce.sh     # env → all experiments → all figures

## Output Structure
results/ must match the committed results/ layout.

## Expected Results
| File | Description | Range |
| results/analysis/curve.csv | cost–reliability data | — |
| results/figures/fig1.png   | Fig.1 cost–reliability | — |
| ... | ... | ... |

## Known Differences
- GPU model may cause float variance (±1e-6)
- API non-determinism may shift sampling, but conclusions stay within tolerance
- Tolerance band: core metric fluctuation ≤ ±0.5%
```

---

## 6. Experiment log specification (EXPERIMENT_LOG.md)

One record per experiment, from day one:

```markdown
## [2026-09-26] Baseline Run - Qwen2.5-3B on Logic Tasks
- **Config**: configs/baseline.yaml
- **Seed**: 42
- **Model**: Qwen2.5-3B-Instruct @ commit a1b2c3d
- **Task**: Logic reasoning, 100 questions
- **Rounds**: 5
- **Status**: completed / failed / running
- **Notes**: accuracy plateaued after round 3; 2 oscillations in round 5
- **Git Commit**: a1b2c3d4e5f6
- **Log File**: logs/20260926_baseline.log
```

---

## 7. Data management

- **Preferred**: public datasets, full acquisition method in paper + README.
- **Next**: self-built datasets with full generation code + seeds.
- **If data cannot be public** (e.g. licensing): provide the full generation process and parameters so others can rebuild an equivalent dataset.
- **Versioning**: hash files (`sha256sum data/processed/task_bank.json`); record the hash in README and EXPERIMENT_LOG.

---

## 8. Ablation matrix (mandatory reporting)

| ID | Condition | Alternative explanation ruled out |
|---|---|---|
| A1 | No evaluator; model self-loops N rounds | gain is from "more rounds", not the evaluator |
| A2 | Evaluator gives random feedback (no prior) | gain is from "correct direction", not "someone to check" |
| A3 | No voting; take first revision | gain is from "aggregating candidates", not correction |
| A4 | Uniform prior instead of statistical prior | gain is from "prior existence", not prior quality |
| A5 | Different temperature (0 / 0.7 / 1.0) | sampling randomness |
| A6 | Different feedback strength (Top-1 / Top-3 / Top-5) | signal-strength effect |

---

## 9. Pre-submission reproducibility checklist

**Code** — deps pinned; no hard-coded params; one commit+tag per experiment; one-command reproduction; script verified runnable by the author.

**Data** — clear provenance; hashes recorded; preprocessing fully documented.

**Experiment** — all seeds fixed and recorded; temperature/params explicit; ≥ 3 independent runs; full ablation matrix; complete experiment log.

**Docs** — appendix config manifest complete (model/evaluator/experiment/judge/hardware); judge prompt verbatim; feedback template verbatim; raw outputs downloadable; known differences + tolerance declared.

---

*This standard is effective 2026-09-26. Any new experiment must comply.*

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-26 | Translated to English; added §0 mapping to the current repository. |