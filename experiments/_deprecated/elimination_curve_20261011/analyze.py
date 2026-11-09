import json
from pathlib import Path
ROOT = Path("/Users/kevin/PycharmProjects/AgentEvaluation")
OUT = ROOT / "experiments/elimination_curve_20261011"
recs = [json.loads(l) for l in open(OUT / "records.jsonl", encoding="utf-8")]
n_aborted = sum(1 for r in recs if r["aborted"])
n_fc = sum(1 for r in recs if r["final_correct"] is True)
print(f"questions={len(recs)} aborted={n_aborted} final_correct={n_fc} acc={n_fc/len(recs):.3f}")
print(f"(A3 mode baseline=0.455 ; random final-survivor = mean 1/n)")
print("\nper-question (n_orig, correct_killed@step[-1=survived], final_correct, aborted):")
for r in recs:
    kill = next((s["step"] for s in r["steps"] if s["eliminated_correct"]), None)
    tag = "survived" if kill is None else f"killed@{kill}"
    print(f"  {r['n_orig']:>2} {r['task_id']:<10} {tag:<12} fc={r['final_correct']} ab={r['aborted']}")
print("\n  k  n_elig  semantic  random  gap")
sem, rnd = [], []
ambiguities = []  # questions with >1 is_correct candidate -> kill signal unreliable
for r in recs:
    kills = [s["step"] for s in r["steps"] if s["eliminated_correct"]]
    if len(kills) > 1:
        ambiguities.append(r["task_id"])
max_n = max(r["n_orig"] for r in recs)
for k in range(max_n):
    elig = [r for r in recs if r["n_orig"] > k]
    if not elig: break
    alive = sum(1 for r in elig
                if (next((s["step"] for s in r["steps"] if s["eliminated_correct"]), None) or 10**9) > k)
    s = alive/len(elig)
    rr = sum((r["n_orig"]-k)/r["n_orig"] for r in elig)/len(elig)
    sem.append((k,s,len(elig))); rnd.append((k,rr,len(elig)))
    print(f"{k:>3}  {len(elig):>3}     {s:.3f}     {rr:.3f}   {s-rr:+.3f}")
print(f"\nAUC semantic={sum(x[1] for x in sem):.3f}  random={sum(x[1] for x in rnd):.3f}")
print(f"questions with >1 correct-eliminated step (normalization ambiguity): {ambiguities}")
out = {"n_questions":len(recs),"n_aborted":n_aborted,"final_survivor_accuracy":n_fc/len(recs),
       "a3_mode_baseline":0.455,"survival_semantic":sem,"survival_random":rnd,
       "per_question":[{"task_id":r["task_id"],"n_orig":r["n_orig"],
         "kill_step":next((s["step"] for s in r["steps"] if s["eliminated_correct"]),None),
         "final_correct":r["final_correct"],"aborted":r["aborted"]} for r in recs]}
(OUT/"survival.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
print("[saved] survival.json")
