"""Audit A3C3 round-0 verdict vs commit, and dump end_state=2 misled traces.

Purpose (2026-10-24): after finding that A3C3's critic silently dropped the solver
CoT, verify whether the round-0 init=0.8889 is a genuine self-consistency gain or an
artefact of scoring the winner's raw final_answer instead of the voted committed key;
and inspect the two end_state=2 tasks to see WHY the feedback loop reversed them.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAJ = ROOT / "experiments/feedback_loop_A3C3_flip19_new_20261023/deepseek-v4-flash/loop_trajectories.jsonl"


def brief_dir(cd):
    if not cd:
        return None
    out = []
    for d in cd:
        name = d.get("archetype_name") or d.get("id")
        susp = (d.get("suspicion") or "")[:60]
        out.append(f"{name}: {susp}")
    return out


rows = [json.loads(l) for l in TRAJ.read_text().splitlines() if l.strip()]
print(f"n_tasks={len(rows)}")
for t in rows:
    tid = t["task_id"]
    gold = t["gold_answer"]
    es = t["end_state"]
    rounds = t["rounds"]
    r0 = rounds[0]
    print(f"\n{'='*70}")
    print(f"{tid}  gold={gold!r}  start={t['start_correct']} final={t['final_correct']} end_state={es} n={t['n_rounds']}")
    print(f"  round0_sample_corrects={t.get('round0_sample_corrects')}")
    print(f"  r0 final_answer={r0['final_answer']!r}")
    print(f"  r0 committed_answer={r0.get('committed_answer')!r}  is_correct={r0['is_correct']}")
    if es != 2:
        continue
    # dump the full trace for the misled (start-correct -> final-wrong) tasks
    for r in rounds:
        print(f"    r{r['round']} correct={r['is_correct']} carried={r.get('carried')} "
              f"commit={r.get('committed_answer')!r} src={r.get('commit_source')}")
        print(f"         dir={brief_dir(r.get('critic_direction'))}")