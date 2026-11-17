#!/usr/bin/env bash
# C2Q question-only critique loop on the 800 new questions
# (docs/SELECTION_CONFIRMATION_ADDENDUM.md). Same params/critic/failure handling as the
# original ctrl_C2Q run (CONTENT_CONTROLS_SPEC v2.2); natural stop (early-stop 3, max 10).
# Round 0 reuses conf_A's deterministic T=0 answer. Critic tokens recorded per round.
# checkpoint-resumable: `health` writes the first 16 questions, `full` resumes to 800.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
SRC="experiments/conf_A_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"
OUT="conf_C2Q_qwen3.8-flash-payg"
TASKS16="hle_401,hle_402,hle_403,hle_404,hle_405,hle_406,hle_407,hle_408,hle_409,hle_410,hle_411,hle_412,hle_413,hle_414,hle_415,hle_416"

MODE="${1:-full}"
if [ "$MODE" = "health" ]; then
  echo "=== C2Q health check (16 questions) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm --tasks "$TASKS16" \
    --arm C2Q --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir "$OUT"
else
  echo "=== C2Q full (800 questions) -> experiments/$OUT ==="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm \
    --arm C2Q --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir "$OUT"
fi
echo "C2Q_DONE"
