#!/usr/bin/env bash
# Second-model replication (docs/REPLICATION_SPEC.md). One command, sequential arms, resume-friendly.
# Usage:  MODEL=<registry name> bash scripts/run_replication.sh [concurrency]
#         then: MODEL=... TASKFILE=data/raw/hle/hle_replication_rest200.json bash scripts/run_replication.sh  (extends to 400)
# The model must be registered in src/config.py PHASE1_MODELS and reachable (run scripts/probe_endpoints.py first).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
MODEL="${MODEL:?set MODEL=<registry name, e.g. qwen3.8-flash-payg or glm-5.3>}"
CONC="${1:-6}"
TASKFILE="${TASKFILE:-data/raw/hle/hle_replication_200.json}"   # second pass: TASKFILE=data/raw/hle/hle_replication_rest200.json (same out-dirs, resume adds the items)
TASKS="$(python3 -c "import json;print(','.join(json.load(open('$TASKFILE'))['task_ids']))")"
TAG="rep200"
run() {  # arm out_dir extra...
  local arm="$1"; local out="$2"; shift 2
  echo "== [$(date '+%F %T')] $MODEL arm=$arm -> experiments/$out"
  python3 src/run_feedback_loop.py --models "$MODEL" --task-set hle --tasks "$TASKS" \
      --arm "$arm" --max-rounds 10 --early-stop 3 --rationale-mode off --tier C \
      --concurrency "$CONC" --out-dir "$out" "$@" 2>&1 | tee -a "experiments/${TAG}_${MODEL}_run.log" | tail -3
}
export CRITIC_HOLD_ON_REPEAT=0
# 1. the model's own greedy round 0 (A arm) — all other arms seed from it
run A "${TAG}_A_${MODEL}" --max-rounds 0 --temperature 0
export A_SOURCE_TRAJ="$PWD/experiments/${TAG}_A_${MODEL}/${MODEL}/loop_trajectories.jsonl"
test -s "$A_SOURCE_TRAJ" || { echo "A arm trajectory missing: $A_SOURCE_TRAJ"; exit 1; }
# 2. loop arms
run A2  "${TAG}_A2_${MODEL}"  --temperature 0
run C2  "${TAG}_C2_${MODEL}"  --temperature 0
run A2P "${TAG}_A2P_${MODEL}" --temperature 0
run A3  "${TAG}_A3_${MODEL}"  --temperature 0.7
echo "== done. Next: scoring per docs/REPLICATION_SPEC.md §4 (T1->T2->T3 K=1->K=3), sidecar is_correct_t3_sidecar_rep.json"
