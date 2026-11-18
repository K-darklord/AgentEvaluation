#!/usr/bin/env bash
# A3Y: continue conf_A3 (equal-token sampling) to the critique-loop token budget on the
# 800 new questions (docs/EQUAL_TOKEN_SAMPLES_SPEC.md). Existing conf_A3 samples
# (rounds 1..9) are kept verbatim; sampling continues (T=0.7) until the per-question
# solver prompt+completion token budget (EXCLUDING round 0) is reached, capped at 100
# samples total (rounds 1..100). checkpoint-resumable: `health` resumes the first 16
# questions, `full` resumes all 800.
# Usage: bash scripts/run_a3y_confirm.sh <qwen|deepseek> [health|full]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0

MODEL_KEY="${1:?usage: run_a3y_confirm.sh <qwen|deepseek> [health|full]}"
MODE="${2:-full}"

case "$MODEL_KEY" in
  qwen)     M=qwen3.8-flash-payg;      BUDGET=experiments/hle400/t3/yoke_budget_qwen_confirm.json ;;
  deepseek) M=deepseek-v4-flash-payg;  BUDGET=experiments/hle400/t3/yoke_budget_deepseek_confirm.json ;;
  *) echo "unknown model: $MODEL_KEY" >&2; exit 1 ;;
esac

CONC=120
export RESUME_TRAJ="$PWD/experiments/conf_A3_$M/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/experiments/conf_A_$M/$M/loop_trajectories.jsonl"
export YOKE_BUDGET_FILE="$PWD/$BUDGET"
OUT="conf_A3Y_$M"
TASKS16="hle_401,hle_402,hle_403,hle_404,hle_405,hle_406,hle_407,hle_408,hle_409,hle_410,hle_411,hle_412,hle_413,hle_414,hle_415,hle_416"

TASKS_ARG=()
if [ "$MODE" = "health" ]; then TASKS_ARG=(--tasks "$TASKS16"); fi

echo "=== A3Y $MODE ($MODEL_KEY) -> experiments/$OUT ==="
python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm "${TASKS_ARG[@]}" \
  --arm A3 --max-rounds 100 --early-stop 3 --rationale-mode off --tier C \
  --temperature 0.7 --concurrency "$CONC" --out-dir "$OUT"
echo "A3Y_DONE"
