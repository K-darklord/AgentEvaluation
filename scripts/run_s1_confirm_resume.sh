#!/usr/bin/env bash
# S1 confirmation run (resume after A-arm 3-question timeout fix). Sequential arms,
# checkpoint-resumable. A2/A2P/C2 continue from the 16-question health-check prefix.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
SRC="experiments/conf_A_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"

echo "=== S1 A2 arm ==="
python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
  --arm A2 --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
  --temperature 0 --concurrency "$CONC" --out-dir conf_A2_qwen3.8-flash-payg

echo "=== S1 A2P arm ==="
python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
  --arm A2P --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
  --temperature 0 --concurrency "$CONC" --out-dir conf_A2P_qwen3.8-flash-payg

echo "=== S1 C2 arm ==="
python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
  --arm C2 --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
  --temperature 0 --concurrency "$CONC" --out-dir conf_C2_qwen3.8-flash-payg

echo "=== S1 budget ==="
python3 scripts/make_yoke_budget.py \
  --c2 experiments/conf_C2_qwen3.8-flash-payg/$M \
  --out experiments/hle400/t3/yoke_budget_qwen_confirm.json

export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_qwen_confirm.json"

echo "=== S1 A2PY arm ==="
python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
  --arm A2P --max-rounds 100 --early-stop 3 --rationale-mode off --tier C \
  --temperature 0 --concurrency "$CONC" --out-dir conf_A2PY_qwen3.8-flash-payg

echo "S1_ALL_DONE"
