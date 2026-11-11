#!/usr/bin/env python3
"""Diagnostic for surface-form vote splitting: vote after merging all correct answers of an item into one
candidate (gold-informed, applied identically to every arm; wrong answers stay split by key).
Expected score with random ties. Also: share of correct rounds not on the item's most common correct key.
Usage: python3 scripts/merge_correct_vote.py"""
import json,sys,importlib.util
sys.path.insert(0,'.')
from pathlib import Path
from collections import Counter
spec=importlib.util.spec_from_file_location('reco','scripts/recompute_evaluator_offline.py'); reco=importlib.util.module_from_spec(spec); spec.loader.exec_module(reco)
side=json.load(open(__import__('os').environ.get('SIDECAR','experiments/hle400/t3/is_correct_t3_sidecar_v3.json')))['arms']
gold_type={}
for arm,d in (('A2','deepseek-v4-flash'),('A2P','deepseek-v4-flash-payg'),('A3','deepseek-v4-flash'),('C3','deepseek-v4-flash'),('C2','deepseek-v4-flash-payg')):
    edir='hle400_A2PRIME' if arm=='A2P' else f'hle400_{arm}'
    loop=reco.load_jsonl(Path(f'experiments/{edir}/{d}/loop_trajectories.jsonl'))
    st=1 if arm=='A3' else 0
    plain=merged=0.0; split=tot=0; ncorr_keys=Counter()
    for t,lp in loop.items():
        keys=reco.freeze_keys(lp.get('gold_answer',''),lp)[st:]; sl=side[arm][t][st:]
        # plain vote, random ties, candidate correct if its last occurrence is correct
        cnt=Counter(k for k in keys if k is not None)
        if cnt:
            top=max(cnt.values()); tied=[k for k in cnt if cnt[k]==top]
            plain+=sum(bool(reco.last_key_correct(keys,sl,k)) for k in tied)/len(tied)
        m=Counter()
        for k,s in zip(keys,sl):
            if k is None: continue
            m['__C__' if s['c'] else k]+=1
        if m:
            top=max(m.values()); tied=[k for k in m if m[k]==top]
            merged+=('__C__' in tied)/len(tied)
        ck=Counter(k for k,s in zip(keys,sl) if k is not None and s['c'])
        if ck:
            tot+=sum(ck.values()); split+=sum(ck.values())-max(ck.values()); ncorr_keys[min(len(ck),4)]+=1
    print(f"{arm:4s} plain {plain:.1f}  merged-correct {merged:.1f}  gain {merged-plain:+.1f}  | correct rounds off the main correct key {split}/{tot}={split/tot:.3f}  items by #distinct correct keys {dict(sorted(ncorr_keys.items()))}")
