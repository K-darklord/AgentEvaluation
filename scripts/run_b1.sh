#!/usr/bin/env bash
# B1 BBEH run (docs/SECOND_BENCHMARK_SPEC.md). qwen3.8-flash-payg.
# Six arms (A / A2 / A2P / C2 / A3 / A2PY) x two groups (hard 800 / easy 240).
# Loop settings, stop rules, token cap, critic prompt and the five generic-doubt
# archetypes are UNCHANGED from the HLE run (max-rounds 10 / early-stop 3, T=0; A3 T=0.7;
# A2PY token-yoked, max-rounds 100). CRITIC_HOLD_ON_REPEAT=0.
# checkpoint-resumable: `health` writes the first 16 questions, `full` resumes to all.
# Usage: bash scripts/run_b1.sh <hard|easy> <arm> [health|full]   arm in {A,A2,A2P,C2,A3,A2PY}
set -eo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
GROUP="${1:?usage: run_b1.sh <hard|easy> <arm> [health|full]}"
ARM="${2:?usage: run_b1.sh <hard|easy> <arm> [health|full]}"
MODE="${3:-full}"

TS="bbeh_hard"
TASKS16="bbeh_b1_multistep_arithmetic_000,bbeh_b1_multistep_arithmetic_001,bbeh_b1_multistep_arithmetic_002,bbeh_b1_multistep_arithmetic_003,bbeh_b1_multistep_arithmetic_004,bbeh_b1_multistep_arithmetic_005,bbeh_b1_multistep_arithmetic_006,bbeh_b1_multistep_arithmetic_007,bbeh_b1_multistep_arithmetic_008,bbeh_b1_multistep_arithmetic_009,bbeh_b1_multistep_arithmetic_010,bbeh_b1_multistep_arithmetic_011,bbeh_b1_multistep_arithmetic_012,bbeh_b1_multistep_arithmetic_013,bbeh_b1_multistep_arithmetic_014,bbeh_b1_multistep_arithmetic_015"
if [ "$GROUP" = "easy" ]; then
  TS="bbeh_easy"
  TASKS16="bbeh_b1_time_arithmetic_000,bbeh_b1_time_arithmetic_001,bbeh_b1_time_arithmetic_002,bbeh_b1_time_arithmetic_003,bbeh_b1_time_arithmetic_004,bbeh_b1_time_arithmetic_005,bbeh_b1_time_arithmetic_006,bbeh_b1_time_arithmetic_007,bbeh_b1_time_arithmetic_008,bbeh_b1_time_arithmetic_009,bbeh_b1_time_arithmetic_010,bbeh_b1_time_arithmetic_011,bbeh_b1_time_arithmetic_012,bbeh_b1_time_arithmetic_013,bbeh_b1_time_arithmetic_014,bbeh_b1_time_arithmetic_015"
fi

TASKS_ARG=()
if [ "$MODE" = "health" ]; then TASKS_ARG=(--tasks "$TASKS16"); fi

# Loop arms seed round-0 from the A arm; the A arm itself generates round 0.
SRC="experiments/b1_A_${GROUP}_${M}/${M}/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"

run() {
  local arm="$1"; local out="$2"; shift 2
  python3 src/run_feedback_loop.py --models "$M" --task-set "$TS" "${TASKS_ARG[@]}" \
    --arm "$arm" --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --concurrency "$CONC" --out-dir "$out" "$@"
}

case "$ARM" in
  A)
    unset A_SOURCE_TRAJ
    python3 src/run_feedback_loop.py --models "$M" --task-set "$TS" "${TASKS_ARG[@]}" \
      --arm A --max-rounds 0 --rationale-mode off --tier C \
      --temperature 0 --concurrency "$CONC" --out-dir "b1_A_${GROUP}_${M}"
    ;;
  A2)   run A2 "b1_A2_${GROUP}_${M}" --temperature 0 ;;
  A2P)  run A2P "b1_A2P_${GROUP}_${M}" --temperature 0 ;;
  C2)   run C2 "b1_C2_${GROUP}_${M}" --temperature 0 ;;
  A3)   run A3 "b1_A3_${GROUP}_${M}" --temperature 0.7 ;;
  A2PY)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_${GROUP}.json"
    run A2P "b1_A2PY_${GROUP}_${M}" --temperature 0 --max-rounds 100
    ;;
  *)
    echo "unknown arm: $ARM" >&2; exit 1
    ;;
esac
echo "${ARM}_DONE"
