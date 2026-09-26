# Experiment: v3 Full 50-Task Run (2026-09-16)

## Git Reference
- Tag: v3-interference-fix-60pct (5-task validation)
- This run: Full 50-task validation with same code

## Results (REAL DATA)
- Accuracy: 24/50 = 48% (up from 34% baseline = +14pp)
- RI: 305 ok / 0 fail = 100% success (up from 0/105 = 0%)
- Not found: 20/50 (all complete_failures, true model limitation)
- API failures: 0
- Dealbreakers: 2/50

## Causal Attribution
- Bug fixes: +6pp (34% → ~40%)
- Interference fix (INT-14): +8pp (~40% → 48%)
- Total: +14pp

## By Category
- Beat or Miss: 4/7 = 57%
- Complex Retrieval: 2/3 = 67%
- Numerical Reasoning: 5/8 = 63%
- Quantitative Retrieval: 6/9 = 67%
- Qualitative Retrieval: 4/9 = 44%
- Adjustments: 1/4 = 25%
- Financial Modeling: 1/4 = 25%
- Market Analysis: 0/3 = 0%
- Trends: 1/3 = 33%

## By Difficulty
- Easy: 12/22 = 55%
- Medium: 8/16 = 50%
- Hard: 4/12 = 33%
