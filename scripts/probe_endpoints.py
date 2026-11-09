#!/usr/bin/env python3
"""Probe which second-model endpoints answer right now (1 tiny call each). Run on the Mac (needs network):
   python3 scripts/probe_endpoints.py
Prints OK/ERROR per (endpoint, model). Pick a reachable (endpoint, model) pair, make sure it is registered in
src/config.py PHASE1_MODELS (add a *-payg alias if only DashScope answers), then run scripts/run_replication.sh."""
import os,sys,json,urllib.request
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import config
def env():
    p=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'.env')
    for l in open(p):
        if '=' in l and not l.startswith('#'):
            k,v=l.strip().split('=',1); os.environ.setdefault(k,v)
env()
def ping(base,key,model,extra=None):
    body={"model":model,"messages":[{"role":"user","content":"Reply with the single word OK."}],"max_tokens":8}
    if extra: body.update(extra)
    req=urllib.request.Request(base.rstrip('/')+"/chat/completions",data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try: r=json.load(urllib.request.urlopen(req,timeout=60)); return "OK served="+str(r.get("model"))
    except Exception as e: return "ERROR "+str(e)[:160]
for m in ["qwen3.8-flash","qwen3.5-flash","qwen-flash","glm-5.3"]:
    print(f"dashscope  {m:14s} -> {ping(config.DASHSCOPE_BASE_URL,os.environ.get('DASHSCOPE_API_KEY',''),m,{'enable_thinking':False})}")
for m in ["glm-5.3","glm-4.7-flash"]:
    print(f"zhipu      {m:14s} -> {ping(config.ZHIPU_BASE_URL,os.environ.get('ZHIPU_API_KEY',''),m)}")
for m in ["qwen3.8-flash","glm-5.3"]:
    print(f"token-plan {m:14s} -> {ping(config.TOKEN_PLAN_BASE_URL,os.environ.get('TOKEN_PLAN_API_KEY',''),m,{'enable_thinking':False})}")
