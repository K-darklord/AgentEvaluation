# config.py — API keys / model config (真实 LLM 时用)
# 推荐用环境变量，不要硬编码到代码里
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 本地 vLLM / OpenAI 兼容服务
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# 评测全局配置
MAX_TOOL_CALLS_PER_TASK = 50
# Alias for agent.py
MAX_TOOL_CALLS = MAX_TOOL_CALLS_PER_TASK
REQUEST_TIMEOUT = 15
# LLM API 调用超时（秒）。旧代码 LLM client（openai SDK/httpx）未接线任何 timeout，
# 连接挂起时请求可无限阻塞（2026-09-28 d1-baseline 卡死 2.5h、0% CPU、11 个悬挂连接实锤）。
# read 用较大值：qwen3.8-flash 等 reasoning 模型单次推理可能 >60s，避免误杀长推理。
LLM_CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "15"))
LLM_READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "180"))
# Streaming read timeout (seconds) for reasoning endpoints. Non-streaming requests to
# these endpoints never fire httpx read-timeout on a server-side hang (qwen3.8-flash on
# a few hard GPQA items emits zero output and blocks until the runner's coarse deadline),
# so closed-book text generation streams and uses this short per-chunk read timeout to
# detect the hang in seconds and mark the item api_failure instead of freezing the arm.
LLM_STREAM_READ_TIMEOUT = float(os.getenv("LLM_STREAM_READ_TIMEOUT", "60"))
LLM_STREAM_CONNECT_TIMEOUT = float(os.getenv("LLM_STREAM_CONNECT_TIMEOUT", "10"))
LLM_STREAM_WRITE_TIMEOUT = float(os.getenv("LLM_STREAM_WRITE_TIMEOUT", "10"))
LLM_STREAM_POOL_TIMEOUT = float(os.getenv("LLM_STREAM_POOL_TIMEOUT", "10"))
LLM_STREAM_WALL_TIMEOUT = float(os.getenv("LLM_STREAM_WALL_TIMEOUT", "300"))
# Wall-clock deadline on the TOTAL stream (seconds). A keep-alive / never-[DONE] stream
# can otherwise block forever while every per-chunk read stays under its own timeout;
# read is widened 30 -> 60 so a slow-but-alive thinking-mode chunk gap is not misread
# as a hang. (2026-11-08 Q-CUT hang fix)



# ======================================================================
# HuggingFace Inference API agent (baseline via remote inference)
# ======================================================================
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
HF_JUDGE_MODEL = os.getenv("HF_JUDGE_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
HF_BASE_URL = "https://router.huggingface.co/v1"

# Model variants for comparison (baseline stays as V4-Flash)
HF_MODEL_V4_FLASH = "deepseek-ai/DeepSeek-V4-Flash"      # baseline (284B/13B active)
HF_MODEL_V4_PRO = "deepseek-ai/DeepSeek-V4-Pro"          # upgrade (1.6T/49B active)
HF_MODEL_V41_FLASH = "deepseek-ai/DeepSeek-V4.1-Flash"   # V4.1 variant
HF_MODEL_R1 = "deepseek-ai/DeepSeek-R1"                  # reasoning model (CoT)

# ======================================================================
# Finance Agent Benchmark (FAB) data config
# ======================================================================
FAB_PUBLIC_CSV_URL = "https://raw.githubusercontent.com/vals-ai/finance-agent/main/data/public.csv"
FAB_DATA_PATH = os.getenv("FAB_DATA_PATH", "data/raw/fab_public.csv")

# ======================================================================
# Phase-1 task set: math (GSM8K) + logic (LogiQA), finance via FAB above
# ======================================================================
GSM8K_DATA_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
GSM8K_DATA_PATH = os.getenv("GSM8K_DATA_PATH", "data/raw/gsm8k_test.jsonl")
LOGIQA_DATA_URL = "https://raw.githubusercontent.com/lgw863/LogiQA-dataset/master/Test.txt"
LOGIQA_DATA_PATH = os.getenv("LOGIQA_DATA_PATH", "data/raw/logiqa_test.txt")
PHASE1_N_PER_BENCH = int(os.getenv("PHASE1_N_PER_BENCH", "50"))

# MATH-500 (Hendrycks MATH 500-question hard subset) — mirrors HuggingFaceH4/MATH-500
MATH500_DATA_URL = "https://modelscope.cn/datasets/AI-ModelScope/MATH-500/resolve/master/test.jsonl"
MATH500_DATA_PATH = os.getenv("MATH500_DATA_PATH", "data/raw/math500_test.jsonl")

# MMLU-Pro (10-option MCQ, 14 domains) — mirrors TIGER-Lab/MMLU-Pro
MMLU_PRO_DATA_URL = "https://modelscope.cn/datasets/TIGER-Lab/MMLU-Pro/resolve/master/data/test-00000-of-00001.parquet"
MMLU_PRO_DATA_PATH = os.getenv("MMLU_PRO_DATA_PATH", "data/raw/mmlu_pro_test.parquet")

# BFCL (Berkeley Function-Calling Leaderboard) — mirrors gorilla-llm BFCL; we use the
# single-turn 'simple' Python subset (AST_NON_LIVE) as the light-FC L2 anchor.
BFCL_DATA_URL = "https://modelscope.cn/datasets/AI-ModelScope/bfcl_v3/resolve/master/data/train-00000-of-00001.parquet"
BFCL_DATA_PATH = os.getenv("BFCL_DATA_PATH", "data/raw/bfcl_v3_train.parquet")

# AIME 1983-2024 (integer-answer competition math, 0-999) - mirrors di-zhang-fdu/AIME_1983_2024.
# HF router is TCP-blocked in this network; hf-mirror.com is the reachable mirror.
AIME_DATA_URL = "https://hf-mirror.com/datasets/di-zhang-fdu/AIME_1983_2024/resolve/main/AIME_Dataset_1983_2024.csv"
AIME_DATA_PATH = os.getenv("AIME_DATA_PATH", "data/raw/aime_1983_2024.csv")

# GPQA-Diamond (198 hard graduate-science 4-option MCQ) - mirrors Idavidrein/gpqa via ModelScope.
GPQA_DATA_URL = "https://modelscope.cn/datasets/modelscope/gpqa/resolve/master/gpqa_diamond.csv"
GPQA_DATA_PATH = os.getenv("GPQA_DATA_PATH", "data/raw/gpqa_diamond.csv")

# Humanity's Last Exam (HLE) text-only slice - mirrors cais/hle. The ~14% image subset
# is deferred (VLM rework). We use a stratified 50-question pilot (hle_50_pilot.jsonl:
# answer_type/answer/shape/question + hle_id) to validate the exact-match scorer on open
# answer forms (symbolic / integer / word / text), the new non-saturated discriminative axis.
# HLE400 clean redo (2026-10-31): main set = 400 sealed questions (200 fixed old
# pilot+hle150 + 200 new stratified draws, seed=42) from scripts/build_hle_400_set.py.
# Default switched off the deprecated 50-question pilot.
HLE_DATA_PATH = os.getenv("HLE_DATA_PATH", "data/raw/hle/hle_400_new.jsonl")

# BIG-Bench Hard (curated reasoning tasks) - mirrors suzgunmiirc/BIG-Bench-Hard (GitHub raw).
# Curated subset of cheap, clearly scoreable tasks (letter MCQ + short free-form).
BBH_DATA_DIR = os.getenv("BBH_DATA_DIR", "data/raw/bbh")
BBH_TASKS = [
    "geometric_shapes",
    "logical_deduction_three_objects",
    "object_counting",
    "penguins_in_a_table",
    "salient_translation_error_detection",
    "snarks",
    "temporal_sequences",
    "web_of_lies",
    "navigate",
    "multistep_arithmetic_two",
    "boolean_expressions",
]

# Generation budget for the hard reasoning benchmarks (AIME / GPQA-Diamond). Their
# models are reasoning models that spend most of the budget on a hidden CoT before
# emitting the visible answer; at the default 1024 cap the CoT alone truncates the
# answer (finish_reason=length) and the run scores wrong even when the model solved
# it. 8192 is the smallest cap observed to let the visible answer through on the
# hardest AIME items; frozen so the baseline stays comparable across runs.
REASONING_BENCH_MAX_TOKENS = int(os.getenv("REASONING_BENCH_MAX_TOKENS", "8192"))

# Content window reserved AFTER the thinking_budget cap is exhausted, so a reasoning
# model that would otherwise keep writing hidden CoT until finish_reason=length is
# forced to floor a clean visible answer instead (deepseek GPQA fix, 2026-10-18).
# Raised 64 -> 8192 for HLE (2026-10-28): HLE's step-by-step / long-answer forms need
# a visible window far larger than the single option letter AIME/GPQA required.
REASONING_CONTENT_MARGIN = int(os.getenv("REASONING_CONTENT_MARGIN", "8192"))

# Transition self-report budget (rationale_mode="transition"). The "why did you
# change" two-stage collection is a side channel that runs under its OWN prompt; it
# needs an independent budget that leaves room for the visible rationale AFTER the
# reasoning model's hidden CoT. 8192 mirrors REASONING_BENCH_MAX_TOKENS. NOTE: the
# budget alone does NOT fix glm-5.3 -- given the full hard question it reasons until
# ANY cap (8190 @8192 / 32766 @32768) and truncates the rationale to "**". The actual
# fix is truncating the question to a short stem in _collect_transition_rationale
# (run_feedback_loop._RATIONALE_QUESTION_MAX_CHARS), item 16.
TRANSITION_RATIONALE_MAX_TOKENS = int(os.getenv("TRANSITION_RATIONALE_MAX_TOKENS", "8192"))


# ======================================================================
# Scoring tolerance / robustness config
# ======================================================================
SCORING_NUMERIC_TOL = float(os.getenv("SCORING_NUMERIC_TOL", "0.05"))       # relative tolerance for numeric scoring
SCORING_QUANTITATIVE_TOL = float(os.getenv("SCORING_QUANTITATIVE_TOL", "0.5"))  # looser tol for quantitative retrieval
SCORING_RUBRIC_COVERAGE = float(os.getenv("SCORING_RUBRIC_COVERAGE", "0.6"))  # threshold for rubric-based scoring
# Numeric comparison tolerance (e.g. 0.05 = 5% difference allowed)
SCORING_NUMERIC_TOLERANCE = float(os.getenv("SCORING_NUMERIC_TOLERANCE", "0.05"))


# ======================================================================
# Evaluation Standard v2.0 (2026-09-13) — 2-tier continuous scoring
# See EVALUATION_STANDARD.md for full spec
# ======================================================================
# Tier 1: Numeric Accuracy (rule-based, deterministic, continuous 0-1)
T1_NUMERIC_TOLERANCE = float(os.getenv("T1_NUMERIC_TOLERANCE", "0.01"))  # 1% relative tolerance
T1_PASS_THRESHOLD = float(os.getenv("T1_PASS_THRESHOLD", "0.5"))         # min score to pass T1

# Tier 2: LLM Semantic Judgment (continuous 0-1, with dealbreaker)
T2_JUDGE_MODEL = os.getenv("T2_JUDGE_MODEL", "deepseek-v4-pro")  # 最强可达 judge（DeepSeek V4 Pro）；原 HF 名已弃（HF 墙）
T2_JUDGE_BASE_URL = os.getenv("T2_JUDGE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
T2_JUDGE_API_KEY = os.getenv("T2_JUDGE_API_KEY", "") or os.getenv("TOKEN_PLAN_API_KEY", "")
T2_JUDGE_MAX_TOKENS = int(os.getenv("T2_JUDGE_MAX_TOKENS", "500"))  # pro 有 hidden CoT，预留 token 否则 content 被吃空
T2_JUDGE_BASE_URL = os.getenv("T2_JUDGE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
T2_JUDGE_API_KEY = os.getenv("T2_JUDGE_API_KEY", "") or os.getenv("TOKEN_PLAN_API_KEY", "")
T2_PASS_THRESHOLD = float(os.getenv("T2_PASS_THRESHOLD", "0.5"))          # min score to pass T2
# T2 rescue = LLM-assisted parse+judge (framework tier 2), a REGISTERED intervention.
# Only runs on rows T1 already judged wrong, and only when enabled. Zero-API rescoring
# stays deterministic with T2_RESCUE_ENABLED=0 (default).
T2_RESCUE_ENABLED = os.getenv("T2_RESCUE_ENABLED", "0") == "1"
T2_RESCUE_MAX_TOKENS = int(os.getenv("T2_RESCUE_MAX_TOKENS", "1000"))
T2_TEMPERATURE = 0                                                          # reproducibility
T2_MAX_TRAJECTORY_CHARS = int(os.getenv("T2_MAX_TRAJECTORY_CHARS", "4000"))  # truncation for context

# Final aggregation
FINAL_PASS_THRESHOLD = float(os.getenv("FINAL_PASS_THRESHOLD", "0.5"))    # final_score >= this -> pass

# ======================================================================
# T1 retrieve_information chunking (INT-15: document chunking + top-k retrieval)
# ======================================================================
# Frozen hyperparameters for retrieve_information's chunk-and-retrieve rework.
# MUST stay fixed across runs to keep FAB re-score comparable (INT-15).
RETRIEVE_CHUNK_SIZE = int(os.getenv("RETRIEVE_CHUNK_SIZE", "1500"))  # chars/chunk (sentence-aligned)
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "5"))               # top-k chunks returned

# ======================================================================
# Concurrency (ThreadPoolExecutor across tasks / scoring rows)
# ======================================================================
# Number of tasks solved in parallel in runner, and rows scored in parallel in evaluator.
# Tune down if the HF router starts rate-limiting (HTTP 429 / "overloaded").
RUNNER_CONCURRENCY = int(os.getenv("AGENTEVALUATION_CONCURRENCY", "6"))


# ======================================================================
# Phase-1 probe model registry (2026-09-28 updated)
# Phase 1 = 3 mid-tier models, all on Alibaba Token Plan:
#   deepseek-v4-flash-0731 / qwen3.8-flash / glm-5.3.
# weak tier (qwen3.6-flash / glm-4.7-flash) deferred to Phase 2.
# Kimi (4th family) pending Tencent Cloud TokenHub quota.
# strong tier (Claude Opus 5.5 / GPT-6 Astra) deferred to Phase 2/3.
# Each entry feeds HuggingFaceAgent(model=..., token=..., base_url=...).
# ======================================================================
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# Token Plan (personal) dedicated endpoint: sk-sp- prefix key + this domain only.
# NOT interchangeable with DASHSCOPE_* (pay-as-you-go); mixing routes to wrong billing.
TOKEN_PLAN_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

# GPT-6 Astra (strong tier) via the cf.api.fan OpenAI-compatible gateway (2026-10-27).
# Dedicated gateway key (sk- prefix); NOT Token Plan / DashScope / Zhipu. Model id on
# this gateway is "gpt-6-astra" (also serves gpt-5.4 / gpt-5.5 / gpt-6-sol / gpt-6.1-sol,
# gpt-5.6-terra / gpt-5.6-sol). Strong tier was deferred to Phase 2/3; now registered for
# the stronger-model control (rules out "the base model is just weak").
# channel: relay, not citable — third-party transit. Every response MUST record its
# `response.model` (what the server actually served) alongside the request id into run
# metadata; a gateway can silently downgrade gpt-6-astra -> gpt-6-sol, so the requested
# model id cannot be trusted. Consistency check: astra's hard context/max_output ceilings
# are 1.05M / 128K; sol is far smaller. Relay digits go to the appendix only — never a
# headline number.
ASTRA_BASE_URL = os.getenv("ASTRA_BASE_URL", "https://cf.api.fan/v1")
ASTRA_API_KEY = os.getenv("ASTRA_API_KEY", "")
ASTRA_MODEL = os.getenv("ASTRA_MODEL", "gpt-6-astra")

PHASE1_MODELS = {
    "deepseek-v4-flash": {
        "tier": "mid",
        "model": "deepseek-v4-flash-0731",
        "base_url": TOKEN_PLAN_BASE_URL,
        "api_key": os.getenv("TOKEN_PLAN_API_KEY", ""),
        # Fix deepseek GPQA thinking non-convergence (2026-10-18): at model-default
        # thinking ON the hard items reason until ANY cap (length, content empty).
        # thinking_budget forces the CoT to stop-and-commit; REASONING_CONTENT_MARGIN
        # then reserves a visible answer window.
        # Global frozen threshold — all reasoning benches (GPQA/AIME/BBH/
        # MMLU-Pro/MATH500/HLE) run on this same budget.
        # 2026-10-28 HLE note: a 32768 trial was REVERTED back to 16384. Local
        # classification of the finish_reason=length rounds (31/31 across the
        # A3+C3 pilot) showed they are all "ramble" — the model spilling English
        # step-by-step reasoning into the visible answer — not truncated good
        # answers, so a larger budget does NOT fix the length outcome (it can even
        # make rambling worse). The hidden-CoT budget was never the binding
        # constraint; those items are the model's real ceiling.
        "thinking_budget": 16384,
        # Moved off HF router (TCP timeout / HTTP 000) to Alibaba Token Plan
        # origin-supply on 2026-09-28. Same DeepSeek-V4-Flash-0731 model.
    },
    # Pay-as-you-go alias for the same model. SAME DeepSeek-V4-Flash-0731 weights,
    # SAME Bailian backend as the Token Plan entry above; only the billing route
    # differs (sk-ws key vs sk-sp key). Added 2026-11-06 so judge-C / C2 reruns can
    # continue while the token-plan 1-month quota is exhausted (429 insufficient_quota).
    "deepseek-v4-flash-payg": {
        "tier": "mid",
        "model": "deepseek-v4-flash-0731",
        "base_url": DASHSCOPE_BASE_URL,
        "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
        "thinking_budget": 16384,
    },
    "qwen3.8-flash": {
        "tier": "mid",
        "model": os.getenv("QWEN_FLASH_MODEL", "qwen3.8-flash"),
        "base_url": os.getenv("TOKEN_PLAN_BASE_URL", TOKEN_PLAN_BASE_URL),
        "api_key": os.getenv("TOKEN_PLAN_API_KEY", ""),
        # thinking left at model default (qwen3.8-flash defaults to thinking ON).
        # We do NOT disable it — thinking is model capability, not interference.
        # Finance token cost is dominated by tool-loop context growth, not hidden CoT.
    },
    "qwen3.8-flash-payg": {
        "tier": "mid",
        "model": os.getenv("QWEN_FLASH_MODEL", "qwen3.8-flash"),
        "base_url": DASHSCOPE_BASE_URL,
        "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
        # thinking_budget forces hidden CoT to stop at 16384 instead of reasoning until
        # finish_reason=length. max_tokens = 16384 + REASONING_CONTENT_MARGIN(8192) =
        # 24576, matching deepseek's frozen budget. Without it qwen fell to
        # REASONING_BENCH_MAX_TOKENS (8192 total) and truncated hard HLE items
        # (qwen ~12.5k hidden CoT / round). E6 budget-alignment fix (2026-11-08).
        "thinking_budget": 16384,
    },
    "glm-5.3": {
        "tier": "mid",
        "model": "glm-5.3",
        "base_url": TOKEN_PLAN_BASE_URL,
        "api_key": os.getenv("TOKEN_PLAN_API_KEY", ""),
    },
    "glm-5.3-zhipu": {
        "tier": "mid",
        "model": "glm-5.3",
        "base_url": ZHIPU_BASE_URL,
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        # Zhipu glm-5.3 (thinking ON by default, returns reasoning_content). No
        # Alibaba `thinking_budget` param; align the total budget to the frozen
        # 16384 (thinking) + 8192 (content) = 24576 via a model-level max_tokens
        # override (run_feedback_loop reads it). Third-model confirmatory run,
        # docs/THIRD_MODEL_SPEC.md (2026-11-11).
        "max_tokens": 24576,
    },
    # weak tier (qwen3.6-flash @ TokenPlan, glm-4.7-flash @ Zhipu) DEFERRED to Phase 2.
    # Kimi (4th family) pending Tencent Cloud TokenHub quota; add here when confirmed.
}


# ======================================================================
# Tool policy (REGISTERED intervention INT-20)
# ======================================================================
# Which benchmarks expose external retrieval tools. This is a generation-side
# intervention: it changes the agent's tool availability, so it is declared here
# (not hard-coded in agent.py) and recorded in run metadata for reproducibility.
#
#   L1 Base (closed-book): the official harness for these benchmarks evaluates
#       the model WITHOUT tools (GPQA-Diamond, AIME, GSM8K, MATH-500, MMLU-Pro,
#       BIG-Bench Hard are all closed-book). Exposing tools here (a) violates the
#       official protocol, (b) lets reasoning models drift into spontaneous web
#       retrieval (GPQA-Diamond exploded to ~29M prompt tokens per run by calling
#       fetch_url against PubMed/Europe PMC), and (c) contaminates the L1 base
#       measurement with L2 tool ability.
#   L2 Augmentation (tool-native): tools are the point of the benchmark.
#       BFCL = function calling (the schema IS the task); finance/FAB = an
#       open-book agent that must retrieve filings to answer.
# Frozen 2026-10-08; see docs/TOOL_POLICY.md.
CLOSED_BOOK_BENCHMARKS = frozenset({
    "math", "math500", "mmlu_pro", "aime", "gpqa", "bbh", "hle",
})
TOOL_NATIVE_BENCHMARKS = frozenset({
    "bfcl", "finance",
})
