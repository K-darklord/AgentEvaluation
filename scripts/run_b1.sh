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

TASKS400="bbeh_b1_geometric_shapes_000,bbeh_b1_geometric_shapes_001,bbeh_b1_geometric_shapes_002,bbeh_b1_geometric_shapes_003,bbeh_b1_geometric_shapes_004,bbeh_b1_geometric_shapes_005,bbeh_b1_geometric_shapes_006,bbeh_b1_geometric_shapes_007,bbeh_b1_geometric_shapes_008,bbeh_b1_geometric_shapes_009,bbeh_b1_geometric_shapes_010,bbeh_b1_geometric_shapes_011,bbeh_b1_geometric_shapes_012,bbeh_b1_geometric_shapes_013,bbeh_b1_geometric_shapes_014,bbeh_b1_geometric_shapes_015,bbeh_b1_geometric_shapes_016,bbeh_b1_geometric_shapes_017,bbeh_b1_geometric_shapes_018,bbeh_b1_geometric_shapes_019,bbeh_b1_geometric_shapes_020,bbeh_b1_geometric_shapes_021,bbeh_b1_geometric_shapes_022,bbeh_b1_geometric_shapes_023,bbeh_b1_geometric_shapes_024,bbeh_b1_geometric_shapes_025,bbeh_b1_geometric_shapes_026,bbeh_b1_geometric_shapes_027,bbeh_b1_geometric_shapes_028,bbeh_b1_geometric_shapes_029,bbeh_b1_geometric_shapes_030,bbeh_b1_geometric_shapes_031,bbeh_b1_geometric_shapes_032,bbeh_b1_geometric_shapes_033,bbeh_b1_geometric_shapes_034,bbeh_b1_geometric_shapes_035,bbeh_b1_geometric_shapes_036,bbeh_b1_geometric_shapes_037,bbeh_b1_geometric_shapes_038,bbeh_b1_geometric_shapes_039,bbeh_b1_hyperbaton_000,bbeh_b1_hyperbaton_001,bbeh_b1_hyperbaton_002,bbeh_b1_hyperbaton_003,bbeh_b1_hyperbaton_004,bbeh_b1_hyperbaton_005,bbeh_b1_hyperbaton_006,bbeh_b1_hyperbaton_007,bbeh_b1_hyperbaton_008,bbeh_b1_hyperbaton_009,bbeh_b1_hyperbaton_010,bbeh_b1_hyperbaton_011,bbeh_b1_hyperbaton_012,bbeh_b1_hyperbaton_013,bbeh_b1_hyperbaton_014,bbeh_b1_hyperbaton_015,bbeh_b1_hyperbaton_016,bbeh_b1_hyperbaton_017,bbeh_b1_hyperbaton_018,bbeh_b1_hyperbaton_019,bbeh_b1_hyperbaton_020,bbeh_b1_hyperbaton_021,bbeh_b1_hyperbaton_022,bbeh_b1_hyperbaton_023,bbeh_b1_hyperbaton_024,bbeh_b1_hyperbaton_025,bbeh_b1_hyperbaton_026,bbeh_b1_hyperbaton_027,bbeh_b1_hyperbaton_028,bbeh_b1_hyperbaton_029,bbeh_b1_hyperbaton_030,bbeh_b1_hyperbaton_031,bbeh_b1_hyperbaton_032,bbeh_b1_hyperbaton_033,bbeh_b1_hyperbaton_034,bbeh_b1_hyperbaton_035,bbeh_b1_hyperbaton_036,bbeh_b1_hyperbaton_037,bbeh_b1_hyperbaton_038,bbeh_b1_hyperbaton_039,bbeh_b1_linguini_000,bbeh_b1_linguini_001,bbeh_b1_linguini_002,bbeh_b1_linguini_003,bbeh_b1_linguini_004,bbeh_b1_linguini_005,bbeh_b1_linguini_006,bbeh_b1_linguini_007,bbeh_b1_linguini_008,bbeh_b1_linguini_009,bbeh_b1_linguini_010,bbeh_b1_linguini_011,bbeh_b1_linguini_012,bbeh_b1_linguini_013,bbeh_b1_linguini_014,bbeh_b1_linguini_015,bbeh_b1_linguini_016,bbeh_b1_linguini_017,bbeh_b1_linguini_018,bbeh_b1_linguini_019,bbeh_b1_linguini_020,bbeh_b1_linguini_021,bbeh_b1_linguini_022,bbeh_b1_linguini_023,bbeh_b1_linguini_024,bbeh_b1_linguini_025,bbeh_b1_linguini_026,bbeh_b1_linguini_027,bbeh_b1_linguini_028,bbeh_b1_linguini_029,bbeh_b1_linguini_030,bbeh_b1_linguini_031,bbeh_b1_linguini_032,bbeh_b1_linguini_033,bbeh_b1_linguini_034,bbeh_b1_linguini_035,bbeh_b1_linguini_036,bbeh_b1_linguini_037,bbeh_b1_linguini_038,bbeh_b1_linguini_039,bbeh_b1_multistep_arithmetic_000,bbeh_b1_multistep_arithmetic_001,bbeh_b1_multistep_arithmetic_002,bbeh_b1_multistep_arithmetic_003,bbeh_b1_multistep_arithmetic_004,bbeh_b1_multistep_arithmetic_005,bbeh_b1_multistep_arithmetic_006,bbeh_b1_multistep_arithmetic_007,bbeh_b1_multistep_arithmetic_008,bbeh_b1_multistep_arithmetic_009,bbeh_b1_multistep_arithmetic_010,bbeh_b1_multistep_arithmetic_011,bbeh_b1_multistep_arithmetic_012,bbeh_b1_multistep_arithmetic_013,bbeh_b1_multistep_arithmetic_014,bbeh_b1_multistep_arithmetic_015,bbeh_b1_multistep_arithmetic_016,bbeh_b1_multistep_arithmetic_017,bbeh_b1_multistep_arithmetic_018,bbeh_b1_multistep_arithmetic_019,bbeh_b1_multistep_arithmetic_020,bbeh_b1_multistep_arithmetic_021,bbeh_b1_multistep_arithmetic_022,bbeh_b1_multistep_arithmetic_023,bbeh_b1_multistep_arithmetic_024,bbeh_b1_multistep_arithmetic_025,bbeh_b1_multistep_arithmetic_026,bbeh_b1_multistep_arithmetic_027,bbeh_b1_multistep_arithmetic_028,bbeh_b1_multistep_arithmetic_029,bbeh_b1_multistep_arithmetic_030,bbeh_b1_multistep_arithmetic_031,bbeh_b1_multistep_arithmetic_032,bbeh_b1_multistep_arithmetic_033,bbeh_b1_multistep_arithmetic_034,bbeh_b1_multistep_arithmetic_035,bbeh_b1_multistep_arithmetic_036,bbeh_b1_multistep_arithmetic_037,bbeh_b1_multistep_arithmetic_038,bbeh_b1_multistep_arithmetic_039,bbeh_b1_nycc_000,bbeh_b1_nycc_001,bbeh_b1_nycc_002,bbeh_b1_nycc_003,bbeh_b1_nycc_004,bbeh_b1_nycc_005,bbeh_b1_nycc_006,bbeh_b1_nycc_007,bbeh_b1_nycc_008,bbeh_b1_nycc_009,bbeh_b1_nycc_010,bbeh_b1_nycc_011,bbeh_b1_nycc_012,bbeh_b1_nycc_013,bbeh_b1_nycc_014,bbeh_b1_nycc_015,bbeh_b1_nycc_016,bbeh_b1_nycc_017,bbeh_b1_nycc_018,bbeh_b1_nycc_019,bbeh_b1_nycc_020,bbeh_b1_nycc_021,bbeh_b1_nycc_022,bbeh_b1_nycc_023,bbeh_b1_nycc_024,bbeh_b1_nycc_025,bbeh_b1_nycc_026,bbeh_b1_nycc_027,bbeh_b1_nycc_028,bbeh_b1_nycc_029,bbeh_b1_nycc_030,bbeh_b1_nycc_031,bbeh_b1_nycc_032,bbeh_b1_nycc_033,bbeh_b1_nycc_034,bbeh_b1_nycc_035,bbeh_b1_nycc_036,bbeh_b1_nycc_037,bbeh_b1_nycc_038,bbeh_b1_nycc_039,bbeh_b1_sarc_triples_000,bbeh_b1_sarc_triples_001,bbeh_b1_sarc_triples_002,bbeh_b1_sarc_triples_003,bbeh_b1_sarc_triples_004,bbeh_b1_sarc_triples_005,bbeh_b1_sarc_triples_006,bbeh_b1_sarc_triples_007,bbeh_b1_sarc_triples_008,bbeh_b1_sarc_triples_009,bbeh_b1_sarc_triples_010,bbeh_b1_sarc_triples_011,bbeh_b1_sarc_triples_012,bbeh_b1_sarc_triples_013,bbeh_b1_sarc_triples_014,bbeh_b1_sarc_triples_015,bbeh_b1_sarc_triples_016,bbeh_b1_sarc_triples_017,bbeh_b1_sarc_triples_018,bbeh_b1_sarc_triples_019,bbeh_b1_sarc_triples_020,bbeh_b1_sarc_triples_021,bbeh_b1_sarc_triples_022,bbeh_b1_sarc_triples_023,bbeh_b1_sarc_triples_024,bbeh_b1_sarc_triples_025,bbeh_b1_sarc_triples_026,bbeh_b1_sarc_triples_027,bbeh_b1_sarc_triples_028,bbeh_b1_sarc_triples_029,bbeh_b1_sarc_triples_030,bbeh_b1_sarc_triples_031,bbeh_b1_sarc_triples_032,bbeh_b1_sarc_triples_033,bbeh_b1_sarc_triples_034,bbeh_b1_sarc_triples_035,bbeh_b1_sarc_triples_036,bbeh_b1_sarc_triples_037,bbeh_b1_sarc_triples_038,bbeh_b1_sarc_triples_039,bbeh_b1_shuffled_objects_000,bbeh_b1_shuffled_objects_001,bbeh_b1_shuffled_objects_002,bbeh_b1_shuffled_objects_003,bbeh_b1_shuffled_objects_004,bbeh_b1_shuffled_objects_005,bbeh_b1_shuffled_objects_006,bbeh_b1_shuffled_objects_007,bbeh_b1_shuffled_objects_008,bbeh_b1_shuffled_objects_009,bbeh_b1_shuffled_objects_010,bbeh_b1_shuffled_objects_011,bbeh_b1_shuffled_objects_012,bbeh_b1_shuffled_objects_013,bbeh_b1_shuffled_objects_014,bbeh_b1_shuffled_objects_015,bbeh_b1_shuffled_objects_016,bbeh_b1_shuffled_objects_017,bbeh_b1_shuffled_objects_018,bbeh_b1_shuffled_objects_019,bbeh_b1_shuffled_objects_020,bbeh_b1_shuffled_objects_021,bbeh_b1_shuffled_objects_022,bbeh_b1_shuffled_objects_023,bbeh_b1_shuffled_objects_024,bbeh_b1_shuffled_objects_025,bbeh_b1_shuffled_objects_026,bbeh_b1_shuffled_objects_027,bbeh_b1_shuffled_objects_028,bbeh_b1_shuffled_objects_029,bbeh_b1_shuffled_objects_030,bbeh_b1_shuffled_objects_031,bbeh_b1_shuffled_objects_032,bbeh_b1_shuffled_objects_033,bbeh_b1_shuffled_objects_034,bbeh_b1_shuffled_objects_035,bbeh_b1_shuffled_objects_036,bbeh_b1_shuffled_objects_037,bbeh_b1_shuffled_objects_038,bbeh_b1_shuffled_objects_039,bbeh_b1_sportqa_000,bbeh_b1_sportqa_001,bbeh_b1_sportqa_002,bbeh_b1_sportqa_003,bbeh_b1_sportqa_004,bbeh_b1_sportqa_005,bbeh_b1_sportqa_006,bbeh_b1_sportqa_007,bbeh_b1_sportqa_008,bbeh_b1_sportqa_009,bbeh_b1_sportqa_010,bbeh_b1_sportqa_011,bbeh_b1_sportqa_012,bbeh_b1_sportqa_013,bbeh_b1_sportqa_014,bbeh_b1_sportqa_015,bbeh_b1_sportqa_016,bbeh_b1_sportqa_017,bbeh_b1_sportqa_018,bbeh_b1_sportqa_019,bbeh_b1_sportqa_020,bbeh_b1_sportqa_021,bbeh_b1_sportqa_022,bbeh_b1_sportqa_023,bbeh_b1_sportqa_024,bbeh_b1_sportqa_025,bbeh_b1_sportqa_026,bbeh_b1_sportqa_027,bbeh_b1_sportqa_028,bbeh_b1_sportqa_029,bbeh_b1_sportqa_030,bbeh_b1_sportqa_031,bbeh_b1_sportqa_032,bbeh_b1_sportqa_033,bbeh_b1_sportqa_034,bbeh_b1_sportqa_035,bbeh_b1_sportqa_036,bbeh_b1_sportqa_037,bbeh_b1_sportqa_038,bbeh_b1_sportqa_039,bbeh_b1_temporal_sequence_000,bbeh_b1_temporal_sequence_001,bbeh_b1_temporal_sequence_002,bbeh_b1_temporal_sequence_003,bbeh_b1_temporal_sequence_004,bbeh_b1_temporal_sequence_005,bbeh_b1_temporal_sequence_006,bbeh_b1_temporal_sequence_007,bbeh_b1_temporal_sequence_008,bbeh_b1_temporal_sequence_009,bbeh_b1_temporal_sequence_010,bbeh_b1_temporal_sequence_011,bbeh_b1_temporal_sequence_012,bbeh_b1_temporal_sequence_013,bbeh_b1_temporal_sequence_014,bbeh_b1_temporal_sequence_015,bbeh_b1_temporal_sequence_016,bbeh_b1_temporal_sequence_017,bbeh_b1_temporal_sequence_018,bbeh_b1_temporal_sequence_019,bbeh_b1_temporal_sequence_020,bbeh_b1_temporal_sequence_021,bbeh_b1_temporal_sequence_022,bbeh_b1_temporal_sequence_023,bbeh_b1_temporal_sequence_024,bbeh_b1_temporal_sequence_025,bbeh_b1_temporal_sequence_026,bbeh_b1_temporal_sequence_027,bbeh_b1_temporal_sequence_028,bbeh_b1_temporal_sequence_029,bbeh_b1_temporal_sequence_030,bbeh_b1_temporal_sequence_031,bbeh_b1_temporal_sequence_032,bbeh_b1_temporal_sequence_033,bbeh_b1_temporal_sequence_034,bbeh_b1_temporal_sequence_035,bbeh_b1_temporal_sequence_036,bbeh_b1_temporal_sequence_037,bbeh_b1_temporal_sequence_038,bbeh_b1_temporal_sequence_039,bbeh_b1_zebra_puzzles_000,bbeh_b1_zebra_puzzles_001,bbeh_b1_zebra_puzzles_002,bbeh_b1_zebra_puzzles_003,bbeh_b1_zebra_puzzles_004,bbeh_b1_zebra_puzzles_005,bbeh_b1_zebra_puzzles_006,bbeh_b1_zebra_puzzles_007,bbeh_b1_zebra_puzzles_008,bbeh_b1_zebra_puzzles_009,bbeh_b1_zebra_puzzles_010,bbeh_b1_zebra_puzzles_011,bbeh_b1_zebra_puzzles_012,bbeh_b1_zebra_puzzles_013,bbeh_b1_zebra_puzzles_014,bbeh_b1_zebra_puzzles_015,bbeh_b1_zebra_puzzles_016,bbeh_b1_zebra_puzzles_017,bbeh_b1_zebra_puzzles_018,bbeh_b1_zebra_puzzles_019,bbeh_b1_zebra_puzzles_020,bbeh_b1_zebra_puzzles_021,bbeh_b1_zebra_puzzles_022,bbeh_b1_zebra_puzzles_023,bbeh_b1_zebra_puzzles_024,bbeh_b1_zebra_puzzles_025,bbeh_b1_zebra_puzzles_026,bbeh_b1_zebra_puzzles_027,bbeh_b1_zebra_puzzles_028,bbeh_b1_zebra_puzzles_029,bbeh_b1_zebra_puzzles_030,bbeh_b1_zebra_puzzles_031,bbeh_b1_zebra_puzzles_032,bbeh_b1_zebra_puzzles_033,bbeh_b1_zebra_puzzles_034,bbeh_b1_zebra_puzzles_035,bbeh_b1_zebra_puzzles_036,bbeh_b1_zebra_puzzles_037,bbeh_b1_zebra_puzzles_038,bbeh_b1_zebra_puzzles_039"
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
  A3Y)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export RESUME_TRAJ="$PWD/experiments/b1_A3_hard_${M}/${M}/loop_trajectories.jsonl"
    run A3 "b1_A3Y_hard_${M}" --temperature 0.7 --max-rounds 100
    ;;
  GT7)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    run A2P "b1_GT7_hard_${M}" --temperature 0.7 --max-rounds 100
    ;;
  GNM)
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export HIDE_PREVIOUS_ANSWER=1 DROP_KEEP_INSTRUCTION=1
    run A2P "b1_GNM_hard_${M}" --temperature 0 --max-rounds 100
    ;;
  GKI)   # only the 400 questions numbered 000-039; --tasks only in full mode
    export YOKE_BUDGET_FILE="$PWD/experiments/hle400/t3/yoke_budget_bbeh_hard.json"
    export DROP_KEEP_INSTRUCTION=1
    if [ "$MODE" = "full" ]; then
      run A2P "b1_GKI_hard_${M}" --temperature 0 --max-rounds 100 --tasks "$TASKS400"
    else
      run A2P "b1_GKI_hard_${M}" --temperature 0 --max-rounds 100
    fi
    ;;
  *)
    echo "unknown arm: $ARM" >&2; exit 1
    ;;
esac
echo "${ARM}_DONE"
