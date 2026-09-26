# Experiment: INT-12 Transparent Budget + No Fallback (Option D)

## Experiment ID
INT-12-transparent_budget

## Date
2026-09-16 (designed, pending execution)

## Importance
**HIGH** — This experiment tests a foundational evaluation fairness question:
should models know their constraints? If confirmed, this insight could affect
how all agentic benchmarks should be designed (FAB, SWE-agent, OpenAI SDK).

## Hypothesis

### Two-Layer Interference Structure
The current agent has a **dual-layer interference** pattern:

```
Layer 1 (INT-05): max_steps = hidden constraint
  ├─ Model has NO knowledge of step budget (50)
  ├─ Cannot plan search budget accordingly
  └─ May "waste" early steps on exploratory queries

Layer 2 (INT-12): fallback synthesis = compensation for Layer 1
  ├─ When model runs out of invisible budget
  ├─ System forcibly synthesizes answer from context
  └─ This is artificial compensation for the hidden constraint
```

### Core Insight
- max_steps itself is a hidden interference because the model doesn't know about it
- fallback synthesis is NOT a separate interference, but a compensation for Layer 1
- Removing Layer 2 alone (without fixing Layer 1) = double punishment
  (still cut off model + no compensation)

### Primary Hypothesis (H1)
Making max_steps transparent + removing fallback will **increase** accuracy,
because the model can plan its search budget and naturally stop when ready.

### Alternative Hypothesis (H0)
No change — the model is incapable of budget planning regardless of transparency.

## Evidence (Current Baseline) — PRE-EXPERIMENT DATA

### Fallback Usage Analysis (NEW)
From INT-05 trajectories.jsonl analysis:
- **9/50 tasks (18%) triggered fallback synthesis path** (max_steps reached)
- **9/9 fallback outputs returned "Not found in the retrieved documents"** (100%)
- **0/9 fallback outputs were correct** (0% accuracy on fallback tasks)
- Fallback task IDs: fab_006, fab_014, fab_017, fab_023, fab_027, fab_034, fab_040, fab_042, fab_047

### Critical Implication
Since ALL 9 fallback outputs are "Not found" (0% correct), removing fallback
(returning "Not found" directly without LLM call) would produce IDENTICAL
baseline accuracy. This means:
- Option B (remove fallback only) = NO-OP for accuracy
- Option D (transparent budget + remove fallback) is the real test
- The experiment tests whether model can AVOID hitting max_steps at all
  once it knows its budget

### Other Baseline Stats
- INT-05 (max_steps=50, hidden, with fallback): 54% (27/50)
- Avg trajectory size: 58,781 chars (min 5,728 / max 171,045)
- Avg tool_calls per task: 29.8 (max 76)
- 13/50 total "complete_failure" (9 from fallback + 4 from other paths)
- System prompt (agent.py:980-1005) does NOT mention step budget

## Method

### Variables
| Variable | Baseline (INT-05) | Treatment (Option D) |
|---|---|---|
| max_steps | 50 | 50 (same) |
| Model knows budget? | NO | **YES** (added to system prompt) |
| Fallback synthesis? | YES (when max_steps reached) | **NO** (return "Not found") |
| _MAX_DUPLICATE forcing? | YES (3 repeats) | YES (kept, separate concern) |
| Agent model | V4-Flash-0731 | V4-Flash-0731 (same) |
| T2 judge model | V4-Flash-0731 | V4-Flash-0731 (same) |
| T1/T2 logic | unchanged | unchanged |

### Model Version Specification (NEW)
- Agent model: `deepseek-ai/DeepSeek-V4-Flash` (HF router, V4-Flash-0731)
- Judge model: `deepseek-ai/DeepSeek-V4-Flash` (same version)
- HF router base URL: https://router.huggingface.co/v1
- Temperature: 0 (deterministic for both agent and T2 judge)
- T2 voting: 3-round median (correctness), majority (dealbreaker)

### Test Set Specification (NEW)
- Benchmark: Finance Agent Benchmark v1 (FAB v1 public)
- Test set: FAB 50 public tasks
- Source: https://raw.githubusercontent.com/vals-ai/finance-agent/main/data/public.csv
- Data path: data/fab_public.csv (committed)
- Categories: 9 (Adjustments, Beat or Miss, Complex Retrieval, etc.)
- Difficulties: Easy (22), Medium (16), Hard (12)

### FAB Official Practice Comparison (NEW)
Based on vals.ai/benchmarks/finance_agent:
- **FAB official does NOT publish a max_steps limit**
- Top models show latency 271-855 seconds, indicating many tool calls allowed
- FAB analyzes TURNS / TOOL CALLS / ERRORS but does not cap steps
- Industry recommendation (CSDN article): 8-20 tool calls per task as starting point
- Industry practice: soft limit (warn at 70%, hard limit at 100%) preferred over silent cutoff

**Conclusion**: Our max_steps=50 with hidden notification + fallback is a DEVIATION
from FAB official. The transparent budget approach better aligns with FAB philosophy.

### Code Changes Required

**Change 1: System prompt (agent.py:980-1005)**
Add explicit budget notification:
```python
system_msg = (
    "You are a financial research agent. "
    f"IMPORTANT: You have a budget of {max_steps} tool calls. "
    "Plan your search accordingly — once you exhaust this budget, "
    "you MUST output ANSWER. Do not waste calls on exploratory queries.\n"
    "You have access to tools:\n"
    + ...
)
```

**Change 2: Fallback path (agent.py:1116-1137)**
Replace synthesis with explicit "Not found":
```python
else:
    # Max steps reached — FAB style: no forced synthesis
    result.final_answer = "Not found"
    steps.append(TrajectoryStep(
        step=step_num,
        thought="Max steps reached; no forced synthesis (FAB style).",
        tool_name="fallback_generate",
        observation="Not found",
    ))
```

### Confounding Variables Analysis (NEW)

**CV1: System prompt length change**
- Adding budget notification (~50 chars) changes prompt length and content
- If accuracy changes, cannot distinguish: transparency effect vs prompt change effect
- **Control**: Run a second treatment (Option D-placebo) that adds an equal-length
  but budget-irrelevant sentence to system prompt, WITHOUT removing fallback
  - Example: "Note: Tool responses may be cached for efficiency."
  - If Option D-placebo ≈ Baseline → transparency effect is real
  - If Option D-placebo ≠ Baseline → prompt change itself affects results

**CV2: _MAX_DUPLICATE interaction**
- _MAX_DUPLICATE=3 still hidden in Option D
- If model knows budget=50, it may behave differently near _MAX_DUPLICATE threshold
- **Mitigation**: Document _MAX_DUPLICATE in Open Questions; keep constant for now

**CV3: T2 judge sees same trajectories**
- T2 judge will see "you have a budget of 50" in trajectory text
- Judge may score differently knowing model had budget warning
- **Mitigation**: T2 judge only sees trajectory summary, not system prompt directly

## Expected Outcomes

| Outcome | Interpretation | Action |
|---|---|---|
| Treatment > Baseline by +5pp or more | H1 confirmed: hidden budget was interference | Mark INT-12 as confirmed interference |
| Treatment ≈ Baseline (±2pp) | H0: model cannot plan budget regardless | Mark INT-12 as non-interference |
| Treatment < Baseline by -5pp or more | Fallback was actually helping; removing it hurts | Mark INT-12 as inverse interference (fallback helps) |
| Treatment > Baseline by +2 to +4pp | Weak signal; need more samples | Run again with multiple seeds |

### Metric Reporting Plan (NEW)
Beyond headline accuracy, report:
1. **% tasks using fallback path** (target: 9 → 0-3 if transparency works)
2. **Avg tool_calls per task** (baseline 29.8; expect lower if model plans)
3. **T1 vs T2 score breakdown** (T1 deterministic, T2 may shift)
4. **Per-difficulty breakdown** (Easy/Medium/Hard)
5. **Per-category breakdown** (especially Beat-or-Miss, Hard categories)
6. **Fallback task IDs** (which of fab_006/014/017/023/027/034/040/042/047 still fail?)
7. **Time-to-ANSWER distribution** (does model answer earlier with budget info?)

## Execution Plan (when ready)
1. Create branch: `exp/int12-transparent-budget`
2. Apply Change 1 + Change 2 in agent.py
3. Commit code changes
4. Run agent on FAB 50 tasks (estimated ~2 hours, V4-Flash cost)
5. Run evaluator (default T2_MAX_TRAJECTORY_CHARS=4000, V4-Flash judge)
6. Compare to INT-05 baseline (54%)
7. **Optional: Run Option D-placebo** to control for CV1 (additional ~2 hours)
8. Update INTERFERENCE_CAUSAL_TABLE.md with results
9. Update this file with Results section

## Cost Estimate
- Agent run: ~2 hours, V4-Flash cost (~same as INT-05)
- Evaluator: ~5-10 minutes, V4-Flash judge
- Optional placebo run: +2 hours, +50% cost (for CV1 control)
- Total: comparable to INT-05, NO V4-Pro needed

## Relationship to Other Experiments
- Builds on INT-05 (max_steps 25→50): +6pp gain from relaxing constraint
- Addresses root cause of INT-12 (fallback synthesis): tests if constraint
  transparency removes need for fallback
- May inform INT-07 (judge self-eval): if budget is transparent, model may
  produce cleaner trajectories, easier to judge

## Open Questions
1. Should the budget number (50) be exact, or a range (e.g., "around 50")?
   - Exact is more rigorous but may cause models to game the count
   - Range is softer but less reproducible
2. Should _MAX_DUPLICATE rule also be made transparent?
   - Currently hidden (model doesn't know 3 repeats = force synthesis)
   - Could add to system prompt: "repeating same call 3+ times will be stopped"
3. Should the model know which step it's on?
   - Currently: step_num is in trajectory but NOT shown to model in real-time
   - Could add: "Step X/N" prefix to each tool response
4. Should we run Option D-placebo (CV1 control)?
   - Adds cost but strengthens causal claim
   - Recommended if headline result is in +2 to +4pp weak-signal range

## Status
PLANNED (awaiting execution)
