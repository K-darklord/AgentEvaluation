# Experiment: v3 Interference Fix (2026-09-16)

## Run ID
`20260916_115752`

## Git Reference
- Tag: `v3-interference-fix-60pct`
- Commit: `b1a02d9`
- Baseline tag: `v0-baseline-34pct` (commit `0db69f0`, 34% on 50 tasks)

## Configuration
- Model: deepseek-ai/DeepSeek-V4-Flash
- Benchmark: FAB (5 tasks, public subset)
- Agent: HuggingFaceAgent (native Function Calling)
- max_steps: 25

## Interference Fix Applied
- INT-14: retrieve_information made stateful
  - Removed text parameter (LLM cannot pass 2000+ chars as JSON param)
  - parse_html auto-caches output to _DOCUMENT_CACHE
  - retrieve_information searches cached documents, takes only query
  - Cache reset per task

## Results
- Accuracy: 3/5 = 60%
- RI success rate: 95% (19/20)
- Avg latency: 102,768.6 ms (-44% vs v2)

## Comparison
| Version | RI Success | Accuracy | Latency |
|---|---|---|---|
| v0 baseline (50 tasks) | 0% (0/105) | 34% | 807s |
| v1 REQUIRED only (5 tasks) | 0% (0/14) | 40% | N/A |
| v2 cache bug (5 tasks) | 0% (0/12) | 40% | 185s |
| v3 fixed (5 tasks) | 95% (19/20) | 60% | 103s |
