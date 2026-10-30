import json, glob, os, collections

ROOT = "/Users/kevin/PycharmProjects/AgentEvaluation/experiments"
cands = set()

# find candidate "full" trajectory dirs and inspect rationale coverage
rows = []
for p in glob.glob(ROOT + "/**/loop_trajectories.jsonl", recursive=True):
    rel = os.path.relpath(p, ROOT)
    if not any(k in rel for k in ("gpqa_full", "gpqa_001_050", "feedback_loop_C_20261015")):
        continue
    try:
        n = 0
        rmode = None
        fams = collections.Counter()
        n_rec_with_rat = 0
        n_round_rat = 0
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                n += 1
                rmode = r.get("rationale_mode")
                fams[r.get("family")] += 1
                has_rat = any((x.get("rationale") not in (None, "")) for x in r.get("rounds", []))
                if has_rat:
                    n_rec_with_rat += 1
                    n_round_rat += sum(1 for x in r.get("rounds", []) if x.get("rationale") not in (None, ""))
        rows.append((rel, n, rmode, dict(fams), n_rec_with_rat, n_round_rat))
    except Exception as e:
        rows.append((rel, -1, "ERR:" + str(e), {}, 0, 0))

for r in sorted(rows):
    print(f"{r[0]:55s} n={r[1]:4d} mode={r[2]} fam={r[3]} rec_with_rat={r[4]} round_rat={r[5]}")