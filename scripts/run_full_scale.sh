#!/usr/bin/env bash
# Full-scale S1 confirm completion (docs/SELECTION_CONFIRMATION_ADDENDUM.md +
# SELECTION_CONFIRMATION_DEEPSEEK_SPEC.md). Run the remaining arms on all 800
# confirm questions (hle_401..1200). Checkpoint-resumable: re-run to resume.
# Two tracks in parallel (different endpoints):
#   qwen track:     A3 -> C2Q   (round-0 reused from conf_A_qwen, already complete)
#   deepseek track: A -> A2 -> A2P -> C2 -> A3  (A is the round-0 seed, must lead)
cd "$(dirname "$0")/.."

qwen_track() {
  bash scripts/run_a3_confirm.sh full
  bash scripts/run_c2q_confirm.sh full
}
ds_track() {
  bash scripts/run_s1_ds_confirm.sh A full
  bash scripts/run_s1_ds_confirm.sh A2 full
  bash scripts/run_s1_ds_confirm.sh A2P full
  bash scripts/run_s1_ds_confirm.sh C2 full
  bash scripts/run_s1_ds_confirm.sh A3 full
}

qwen_track & Q=$!
ds_track & D=$!
wait $Q; echo "qwen_track_exit=$?"
wait $D; echo "ds_track_exit=$?"
echo "FULL_SCALE_DONE"
