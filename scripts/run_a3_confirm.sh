#!/usr/bin/env bash
# A3 independent-sampling baseline on the 800 new questions
# (docs/SELECTION_CONFIRMATION_ADDENDUM.md). Round 0 reuses conf_A's deterministic
# T=0 answer; rounds 1..9 are i.i.d. T=0.7 samples (self-consistency, no feedback).
# checkpoint-resumable: `health` writes the first 16 questions, `full` resumes to 800.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
SRC="experiments/conf_A_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"
OUT="conf_A3_qwen3.8-flash-payg"
TASKS16="hle_401,hle_402,hle_403,hle_404,hle_405,hle_406,hle_407,hle_408,hle_409,hle_410,hle_411,hle_412,hle_413,hle_414,hle_415,hle_416"

MODE="${1:-full}"
if [ "$MODE" = "health" ]; then
  echo "=== A3 health check (16 questions) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm --tasks "$TASKS16" \
    --arm A3 --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0.7 --concurrency "$CONC" --out-dir "$OUT"
else
  echo "=== A3 full (800 questions) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
    --arm A3 --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0.7 --concurrency "$CONC" --out-dir "$OUT"
fi
echo "A3_DONE"
