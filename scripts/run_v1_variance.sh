#!/usr/bin/env bash
# V1 variance re-run (docs/RUN_VARIANCE_SPEC.md). Re-runs two conditions on the first
# batch of 400 new questions (hle_401..hle_800) with inputs identical to the original
# S1 confirmation run (run_s1_confirm_resume.sh):
#   C2r   = critique loop, round-0 reused from conf_A, settings = conf_C2.
#   A2PYr = token-yoked generic doubt, YOKE_BUDGET_FILE = yoke_budget_qwen_confirm.json
#           (same budget as the original conf_A2PY), settings = conf_A2PY.
# Sequential; checkpoint-resumable (re-run the same command to resume where it stopped).
# Does NOT touch conf_C2 / conf_A2PY (separate out-dirs).
# Usage:  bash scripts/run_v1_variance.sh [all|c2r|a2pyr]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export CRITIC_HOLD_ON_REPEAT=0
M=qwen3.8-flash-payg
CONC=120
SRC="experiments/conf_A_qwen3.8-flash-payg/$M/loop_trajectories.jsonl"
export A_SOURCE_TRAJ="$PWD/$SRC"
# 400 task ids hle_401..hle_800 (first confirm batch).
TASKS400="$(python3 -c "print(','.join(f'hle_{i:03d}' for i in range(401, 801)))")"

MODE="${1:-all}"

run_c2r() {
  echo "== [$(date '+%F %T')] V1 C2r -> experiments/conf_C2r_qwen3.8-flash-payg =="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm --tasks "$TASKS400" \
    --arm C2 --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir conf_C2r_qwen3.8-flash-payg
}

run_a2pyr() {
  export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_qwen_confirm.json"
  echo "== [$(date '+%F %T')] V1 A2PYr -> experiments/conf_A2PYr_qwen3.8-flash-payg =="
  python3 src/run_feedback_loop.py --models "$M" --task-set hle_confirm --tasks "$TASKS400" \
    --arm A2P --max-rounds 100 --early-stop 3 --rationale-mode off --tier C \
    --temperature 0 --concurrency "$CONC" --out-dir conf_A2PYr_qwen3.8-flash-payg
}

case "$MODE" in
  c2r)   run_c2r ;;
  a2pyr) run_a2pyr ;;
  all)   run_c2r; run_a2pyr ;;
  *) echo "usage: $0 [all|c2r|a2pyr]" >&2; exit 1 ;;
esac
echo "V1_RUN_DONE"
