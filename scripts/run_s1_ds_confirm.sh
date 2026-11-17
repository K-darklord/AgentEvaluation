#!/usr/bin/env bash
# S1-DS deepseek confirmation run (docs/SELECTION_CONFIRMATION_DEEPSEEK_SPEC.md).
# All five arms on the pay-as-you-go channel (deepseek-v4-flash-payg). A arm is the
# greedy T=0 round-0 seed; A2/A2P/C2/A3 reuse its round-0 (A_SOURCE_TRAJ). Same params,
# prompts and stop rules as the original deepseek 400 run (max-rounds 10 / early-stop 3,
# temperature 0, A3 temperature 0.7). C2 logs critic tokens per round.
# checkpoint-resumable: `health` writes the first 16 questions, `full` resumes to 800.
# Usage: bash scripts/run_s1_ds_confirm.sh <arm> [health|full]   arm in {A,A2,A2P,C2,A3,A2PY}
set -eo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=deepseek-v4-flash-payg
CONC=120
TASKS16="hle_401,hle_402,hle_403,hle_404,hle_405,hle_406,hle_407,hle_408,hle_409,hle_410,hle_411,hle_412,hle_413,hle_414,hle_415,hle_416"
ARM="${1:?usage: run_s1_ds_confirm.sh <arm> [health|full]}"
MODE="${2:-full}"

TASKS_ARG=()
if [ "$MODE" = "health" ]; then TASKS_ARG=(--tasks "$TASKS16"); fi

# Loop arms seed round-0 from the A arm; the A arm itself generates round 0.
SRC="experiments/conf_A_deepseek-v4-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"

run() {
  local arm="$1"; local out="$2"; shift 2
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm "${TASKS_ARG[@]}" \
    --arm "$arm" --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --concurrency "$CONC" --out-dir "$out" "$@"
}

case "$ARM" in
  A)
    unset A_SOURCE_TRAJ
    python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm "${TASKS_ARG[@]}" \
      --arm A --max-rounds 0 --rationale-mode off --tier C \
      --temperature 0 --concurrency "$CONC" --out-dir "conf_A_$M"
    ;;
  A2)
    run A2 "conf_A2_$M" --temperature 0
    ;;
  A2P)
    run A2P "conf_A2P_$M" --temperature 0
    ;;
  C2)
    run C2 "conf_C2_$M" --temperature 0
    ;;
  A3)
    run A3 "conf_A3_$M" --temperature 0.7
    ;;
  A2PY)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_deepseek_confirm.json"
    run A2P "conf_A2PY_$M" --temperature 0 --max-rounds 100
    ;;
  *)
    echo "unknown arm: $ARM" >&2; exit 1
    ;;
esac
echo "${ARM}_DONE"
