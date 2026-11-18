#!/usr/bin/env bash
# C2QY: continue conf_C2Q to the critique-loop token budget on the 800 new questions
# (docs/SELECTION_CONFIRMATION_ADDENDUM.md, resume mode per EQUAL_TOKEN_CONTROLS_SPEC v4).
# Requires conf_C2Q to be complete first. Existing rounds are kept verbatim; only rounds
# past the budget resume. Questions already over budget are written out unchanged.
# checkpoint-resumable: `health` resumes the first 16 questions, `full` resumes all 800.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
export RESUME_TRAJ="$PWD/experiments/conf_C2Q_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/experiments/conf_A_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_qwen_confirm.json"
OUT="yoke_C2QY_confirm_qwen3.8-flash-payg"
TASKS16="hle_401,hle_402,hle_403,hle_404,hle_405,hle_406,hle_407,hle_408,hle_409,hle_410,hle_411,hle_412,hle_413,hle_414,hle_415,hle_416"

MODE="${1:-full}"
if [ "$MODE" = "health" ]; then
  echo "=== C2QY health check (16 questions, resume) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm --tasks "$TASKS16" \
    --arm C2Q --max-rounds 100 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir "$OUT"
else
  echo "=== C2QY full (800 questions, resume) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
    --arm C2Q --max-rounds 100 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir "$OUT"
fi
echo "C2QY_DONE"
