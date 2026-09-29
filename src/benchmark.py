"""
benchmark.py
=============
真实金融评测集的 schema 定义 + 加载器。

设计原则：数据结构 **完全对齐 Finance Agent Benchmark (arXiv:2508.00828)**，
每条样本含：question / gold_answer / reasoning_steps / rubric / evidence。
这样日后你把 TASKS 换成官方 537 题 (HuggingFace/CSV) 时，下游 runner/scorer 零改动。

本文件自带一个 "live mini benchmark"：从 **公开、无需 key** 的数据源
（公司官网 IR / SEC 公开数字 / 维基百科 infobox）抓取真实财务数字，
确保 pipeline 跑的是「真调用」，而非 mock。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import csv
import urllib.request
import re


@dataclass
class Task:
    task_id: str
    category: str            # 对齐 FAB 九大类: Quantitative Retrieval / Numerical Reasoning ...
    difficulty: str          # Easy / Medium / Hard
    prompt: str              # 给 agent 的题目
    gold_answer: str         # 标准答案
    reasoning_steps: list[str] = field(default_factory=list)  # 专家分步解法
    rubric: list[str] = field(default_factory=list)           # 判分检查项
    evidence: list[str] = field(default_factory=list)        # 证据来源 URL/段落
    metadata: dict = field(default_factory=dict)             # ticker, filing_type 等

    def to_dict(self):
        return asdict(self)


# ======================================================================
# Live mini benchmark：真实可抓取、答案确定的金融问题（无需 API key）
# 注：这些数字来自各公司公开披露的年度报告，抓取后自动与 gold_answer 比对
# ======================================================================
TASKS: list[Task] = [
    Task(
        task_id="live_001",
        category="Quantitative Retrieval",
        difficulty="Easy",
        prompt=(
            "What was NVIDIA's total revenue (in USD millions) for fiscal year 2024? "
            "Use the tool `fetch_url` to retrieve the official annual report, then answer."
        ),
        gold_answer="60922",   # NVDA FY2024 10-K: Revenue = $60,922 million
        reasoning_steps=[
            "Fetch NVIDIA FY2024 (annual report / 10-K) from investor site.",
            "Locate 'Consolidated Statements of Operations' (Income Statement).",
            "Read 'Revenue' line for the fiscal year ended Jan 28, 2024.",
        ],
        rubric=[
            "answer_is_numeric_and_close_to_60922_million",
            "cites_official_source_url",
            "uses_correct_fiscal_year_ending_Jan_2024",
        ],
        evidence=["https://investor.nvidia.com/financial-information/annual-reports/default.aspx"],
        metadata={"ticker": "NVDA", "filing_type": "10-K", "fiscal_year": 2024},
    ),
    Task(
        task_id="live_002",
        category="Numerical Reasoning",
        difficulty="Medium",
        prompt=(
            "Apple Inc. FY2023 net sales were $383,285 million and FY2024 net sales were "
            "$391,035 million. Compute the year-over-year revenue growth rate in percent "
            "(round to two decimals). Use `fetch_url` if you need source confirmation."
        ),
        gold_answer="2.02",  # (391035-383285)/383285 * 100 = 2.0197...
        reasoning_steps=[
            "Identify FY2023 net sales = 383,285 and FY2024 = 391,035 (USD millions).",
            "Compute (391035 - 383285) / 383285.",
            "Multiply by 100 and round to two decimals -> 2.02%.",
        ],
        rubric=[
            "formula_is_correct",
            "result_rounded_to_two_decimals",
            "answer_within_0.05_of_2.02",
        ],
        evidence=["https://www.apple.com/investor-relations/"],
        metadata={"ticker": "AAPL", "filing_type": "10-K", "metric": "revenue_growth_pct"},
    ),
    Task(
        task_id="live_003",
        category="Qualitative Retrieval",
        difficulty="Easy",
        prompt=(
            "Briefly describe the primary business segments of Microsoft as disclosed in "
            "its latest annual report. Use `fetch_url` to retrieve the source."
        ),
        gold_answer="Microsoft operates through three segments: Productivity and Business Processes, "
                    "Intelligent Cloud, and More Personal Computing.",
        reasoning_steps=[
            "Fetch Microsoft latest 10-K / annual report.",
            "Locate 'Business' section describing operating segments.",
            "Summarize the three named segments.",
        ],
        rubric=[
            "lists_all_three_segments",
            "segment_names_accurate",
            "cites_official_source",
        ],
        evidence=["https://www.microsoft.com/investor/reports-and-filings"],
        metadata={"ticker": "MSFT", "filing_type": "10-K", "aspect": "business_segments"},
    ),
]


def load_tasks(path: str | Path | None = None) -> list[Task]:
    """加载 benchmark。若传 path（CSV/JSONL），从文件读；否则用内置 live mini set。"""
    if path is None:
        return TASKS
    p = Path(path)
    tasks: list[Task] = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            tasks.append(Task(**d))
    return tasks


# ======================================================================
# Finance Agent Benchmark (FAB) public dataset loader
# Source: https://github.com/vals-ai/finance-agent (arXiv:2508.00828)
# The full 537-question set is proprietary (gated behind platform.vals.ai).
# The public subset (~50 questions) is in data/public.csv.
# ======================================================================

# Map FAB "Question Type" to Task.category (normalize whitespace quirks).
_FAB_CATEGORY_MAP = {
    "Simple retrieval - Quantitative": "Quantitative Retrieval",
    "Simple retrieval - Qualitative": "Qualitative Retrieval",
    "Complex Retrieval": "Complex Retrieval",
    "Numerical Reasoning": "Numerical Reasoning",
    "Market Analysis": "Market Analysis",
    "Trends": "Trends",
    "Beat or Miss": "Beat or Miss",
    "Financial Modeling  Projections": "Financial Modeling Projections",  # normalize double space
}


def _map_question_type(qtype: str) -> str:
    """I normalize FAB Question Type whitespace and map to a Task category."""
    key = re.sub(r"\s+", " ", qtype.strip())
    return _FAB_CATEGORY_MAP.get(key, key or "Unknown")


def _expert_time_to_difficulty(mins) -> str:
    """I convert FAB expert-time (minutes) to Easy/Medium/Hard."""
    try:
        m = float(mins)
    except (TypeError, ValueError):
        return "Medium"
    if m <= 5:
        return "Easy"
    if m <= 15:
        return "Medium"
    return "Hard"


def _parse_rubric(rubric_str: str) -> tuple[list[str], list[dict]]:
    """I parse FAB Rubric JSON into (plain_criteria_list, structured_for_metadata).
    On parse failure I return ([], []) so the pipeline never crashes on bad data."""
    try:
        items = json.loads(rubric_str)
        if not isinstance(items, list):
            return ([], [])
        plain = [c.get("criteria", "") for c in items if isinstance(c, dict)]
        structured = [c for c in items if isinstance(c, dict)]
        return (plain, structured)
    except (json.JSONDecodeError, TypeError):
        return ([], [])


def _download_fab_csv(dest: Path) -> Path:
    """I download public.csv to dest, creating parent dir if needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/vals-ai/finance-agent/main/data/public.csv",
        str(dest),
    )
    return dest


def load_fab_questions(
    csv_path: str | Path | None = None,
    download: bool = True,
) -> list[Task]:
    """I load FAB public questions from CSV. If csv_path is None I use config.FAB_DATA_PATH.
    If the file does not exist and download=True, I auto-fetch public.csv.
    I map FAB columns to the Task dataclass and synthesize task_id = fab_{idx:03d}.
    FAB ships no evidence URLs, so evidence=[] (agent answers from parametric knowledge).
    """
    from src.config import FAB_DATA_PATH

    if csv_path is None:
        csv_path = FAB_DATA_PATH
    p = Path(csv_path)

    if not p.exists() and download:
        print(f"[FAB] Downloading public.csv to {p} ...")
        _download_fab_csv(p)

    if not p.exists():
        print(f"[FAB] No CSV at {p}; returning empty list.")
        return []

    tasks: list[Task] = []
    with p.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            rubric_plain, rubric_structured = _parse_rubric(row.get("Rubric", "[]"))
            tasks.append(Task(
                task_id=f"fab_{idx:03d}",
                category=_map_question_type(row.get("Question Type", "Unknown")),
                difficulty=_expert_time_to_difficulty(row.get("Expert time (mins)", "")),
                prompt=row.get("Question", "").strip(),
                gold_answer=row.get("Answer", "").strip(),
                reasoning_steps=[],
                rubric=rubric_plain,
                evidence=[],
                metadata={
                    "question_type_raw": row.get("Question Type", ""),
                    "expert_time_mins": row.get("Expert time (mins)", ""),
                    "rubric_structured": rubric_structured,
                },
            ))
    return tasks


# ======================================================================
# Phase-1 task set: math (GSM8K) + logic (LogiQA); finance via load_fab_questions.
# These pure-reasoning domains are added to the probe to build a cross-domain
# error taxonomy. Both fetch from public GitHub mirrors (HF is unreachable here)
# and are cached under data/raw/.
# ======================================================================

def _download_url(url: str, dest: Path, desc: str) -> Path:
    """I download a file from `url` to `dest`, creating parent dirs, and return `dest`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[{desc}] Downloading to {dest} ...")
    urllib.request.urlretrieve(url, str(dest))
    return dest


_GSM8K_FINAL_RE = re.compile(r"####\s*([^\s]+)")


def load_gsm8k_questions(
    jsonl_path: str | Path | None = None,
    download: bool = True,
    limit: int | None = 50,
) -> list[Task]:
    """I load the first `limit` GSM8K test questions (grade-school math word problems).
    The gold answer is the number after the final '####' marker in the answer field.
    Category: Mathematical Reasoning; difficulty: Medium.
    Reproducible: I always take the first `limit` lines of test.jsonl (deterministic)."""
    from src.config import GSM8K_DATA_PATH, GSM8K_DATA_URL

    if jsonl_path is None:
        jsonl_path = GSM8K_DATA_PATH
    p = Path(jsonl_path)

    if not p.exists() and download:
        _download_url(GSM8K_DATA_URL, p, "GSM8K")

    if not p.exists():
        print(f"[GSM8K] No file at {p}; returning empty list.")
        return []

    tasks: list[Task] = []
    with p.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if limit is not None and i > limit:
                break
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            m = _GSM8K_FINAL_RE.search(d.get("answer", ""))
            gold = m.group(1).strip(".,").replace(",", "") if m else ""
            tasks.append(Task(
                task_id=f"gsm8k_{i:03d}",
                category="Mathematical Reasoning",
                difficulty="Medium",
                prompt=d.get("question", "").strip(),
                gold_answer=gold,
                reasoning_steps=[],
                rubric=["final_answer_matches_gold_numeric_answer"],
                evidence=[],
                metadata={"source": "gsm8k", "split": "test", "benchmark": "math"},
            ))
    return tasks


_LOGIQA_OPT_RE = re.compile(r"^\s*([A-E])[\.\)]\s*(.+)$")


def _parse_logiqa(raw_text: str) -> list[dict]:
    """I parse LogiQA-dataset Test.txt into clean question dicts.

    Layout (per block, separated by blank lines):
      line 0  -> answer label (a-e)
      lines.. -> question text (context + question)
      lines.. -> options "A. ...", "B. ...", "C. ...", "D. ...", (optional "E. ...")

    I keep only blocks whose options parse to exactly A,B,C,D(,E) IN ORDER via the
    strict "X." / "X)" delimiter. A few machine-translation-noise blocks (missing or
    merged option delimiters) are skipped deterministically.
    """
    items: list[dict] = []
    for block in re.split(r"\n\s*\n", raw_text):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        answer = lines[0].lower()
        if not re.fullmatch(r"[a-e]", answer):
            continue
        body = lines[1:]

        opt_start = next((k for k, ln in enumerate(body) if _LOGIQA_OPT_RE.match(ln)), None)
        if opt_start is None:
            continue

        question = " ".join(body[:opt_start])
        opts: list[str] = []
        letters: list[str] = []
        for ln in body[opt_start:]:
            m = _LOGIQA_OPT_RE.match(ln)
            if m:
                letters.append(m.group(1))
                opts.append(f"{m.group(1)}. {m.group(2).strip()}")
            elif opts:
                opts[-1] += " " + ln   # continuation text glued to previous option

        if letters == list("ABCD") or letters == list("ABCDE"):
            items.append({"answer": answer, "question": question, "options": opts})
    return items


def load_logic_questions(
    txt_path: str | Path | None = None,
    download: bool = True,
    limit: int | None = 50,
) -> list[Task]:
    """I load the first `limit` LogiQA test questions (multiple-choice logical reasoning).
    The gold answer is the correct option letter (A-E). Category: Logical Reasoning;
    difficulty: Medium. Reproducible: first `limit` cleanly-parseable questions."""
    from src.config import LOGIQA_DATA_PATH, LOGIQA_DATA_URL

    if txt_path is None:
        txt_path = LOGIQA_DATA_PATH
    p = Path(txt_path)

    if not p.exists() and download:
        _download_url(LOGIQA_DATA_URL, p, "LogiQA")

    if not p.exists():
        print(f"[LogiQA] No file at {p}; returning empty list.")
        return []

    raw = p.read_text(encoding="utf-8")
    items = _parse_logiqa(raw)
    if limit is not None:
        items = items[:limit]

    tasks: list[Task] = []
    for i, it in enumerate(items, start=1):
        prompt = it["question"] + "\n" + "\n".join(it["options"])
        tasks.append(Task(
            task_id=f"logic_{i:03d}",
            category="Logical Reasoning",
            difficulty="Medium",
            prompt=prompt,
            gold_answer=it["answer"].upper(),
            reasoning_steps=[],
            rubric=["selects_the_correct_option_letter"],
            evidence=[],
            metadata={"source": "logiqa", "split": "test", "benchmark": "logic"},
        ))
    return tasks


_MATH500_BOXED_RE = re.compile(r"\\boxed\{([^}]*)\}")

def _math500_answer(d: dict) -> str:
    """I return MATH-500's gold answer: the explicit `answer` field when present,
    else the expression inside the final \\boxed{} of the solution."""
    ans = str(d.get("answer", "")).strip()
    if ans:
        return ans
    m = _MATH500_BOXED_RE.search(d.get("solution", ""))
    return m.group(1).strip() if m else ""


def load_math500_questions(
    jsonl_path: str | Path | None = None,
    download: bool = True,
    limit: int | None = 50,
) -> list[Task]:
    """I load the first `limit` MATH-500 test questions (hard competition math).
    Gold answer is the LaTeX expression from the `answer` field (fallback \\boxed{}).
    Category: Mathematical Reasoning; difficulty: Hard. Reproducible: first `limit` lines."""
    from src.config import MATH500_DATA_PATH, MATH500_DATA_URL

    if jsonl_path is None:
        jsonl_path = MATH500_DATA_PATH
    p = Path(jsonl_path)

    if not p.exists() and download:
        _download_url(MATH500_DATA_URL, p, "MATH-500")

    if not p.exists():
        print(f"[MATH-500] No file at {p}; returning empty list.")
        return []

    tasks: list[Task] = []
    with p.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if limit is not None and i > limit:
                break
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            tasks.append(Task(
                task_id=f"math500_{i:03d}",
                category="Mathematical Reasoning",
                difficulty="Hard",
                prompt=d.get("problem", "").strip(),
                gold_answer=_math500_answer(d),
                reasoning_steps=[],
                rubric=["final_answer_matches_gold_math_expression"],
                evidence=[],
                metadata={"source": "math500", "split": "test", "benchmark": "math500",
                          "subject": d.get("subject", ""), "level": d.get("level", "")},
            ))
    return tasks


_MMLU_OPT_LETTERS = "ABCDEFGHIJ"


def load_mmlu_pro_questions(
    parquet_path: str | Path | None = None,
    download: bool = True,
    limit: int | None = 50,
) -> list[Task]:
    """I load the first `limit` MMLU-Pro test questions (10-option MCQ, 14 domains).
    The gold answer is the option letter (A-J). Category: Logical Reasoning; Hard.
    Reproducible: head(`limit`) rows of the test parquet (deterministic row order)."""
    from src.config import MMLU_PRO_DATA_PATH, MMLU_PRO_DATA_URL

    if parquet_path is None:
        parquet_path = MMLU_PRO_DATA_PATH
    p = Path(parquet_path)

    if not p.exists() and download:
        _download_url(MMLU_PRO_DATA_URL, p, "MMLU-Pro")

    if not p.exists():
        print(f"[MMLU-Pro] No file at {p}; returning empty list.")
        return []

    import pandas as pd

    df = pd.read_parquet(p)
    if limit is not None:
        df = df.head(limit)

    tasks: list[Task] = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        options = [str(o) for o in list(row["options"])]
        opt_lines = [f"{_MMLU_OPT_LETTERS[j]}. {opt}" for j, opt in enumerate(options)]
        prompt = f"{row['question']}\n" + "\n".join(opt_lines)
        gold = str(row["answer"]).strip().upper()
        tasks.append(Task(
            task_id=f"mmlu_pro_{i:03d}",
            category="Logical Reasoning",
            difficulty="Hard",
            prompt=prompt,
            gold_answer=gold,
            reasoning_steps=[],
            rubric=["selects_the_correct_option_letter"],
            evidence=[],
            metadata={"source": "mmlu_pro", "split": "test", "benchmark": "mmlu_pro",
                      "subject": str(row.get("category", "")), "n_options": len(options)},
        ))
    return tasks


def _bfcl_user_query(turns) -> str:
    """I extract the user query from a BFCL `turns` list: the last user message of turn 0."""
    if not turns:
        return ""
    turn0 = turns[0]
    for m in reversed(turn0):
        if m.get("role") == "user":
            return str(m.get("content", "")).strip()
    return ""


def _json_field(value):
    """I parse a BFCL JSON-string column (tools / functions / ground_truth are stored as
    JSON strings in the parquet) into a Python object. On parse failure I return the raw
    value unchanged so the pipeline never crashes on malformed data."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def load_bfcl_questions(
    parquet_path: str | Path | None = None,
    download: bool = True,
    limit: int | None = 50,
    test_category: str = "simple",
) -> list[Task]:
    """I load BFCL single-turn function-calling questions (light-FC L2 anchor).
    I keep only `test_category == 'simple'` (single function, single turn, Python),
    which measures native function-calling in isolation at near-zero retrieval cost.
    gold_answer holds the BFCL AST ground-truth JSON; metadata carries the OpenAI-format
    `tools` list so the agent can invoke native function calling directly."""
    from src.config import BFCL_DATA_PATH, BFCL_DATA_URL

    if parquet_path is None:
        parquet_path = BFCL_DATA_PATH
    p = Path(parquet_path)

    if not p.exists() and download:
        _download_url(BFCL_DATA_URL, p, "BFCL")

    if not p.exists():
        print(f"[BFCL] No file at {p}; returning empty list.")
        return []

    import pandas as pd

    df = pd.read_parquet(p)
    df = df[(df["test_category"] == test_category) & (~df["multi_turn"].fillna(False))]
    if limit is not None:
        df = df.head(limit)

    tasks: list[Task] = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        turns = json.loads(row["turns"])
        prompt = _bfcl_user_query(turns)
        gt = json.dumps(_json_field(row["ground_truth"]), ensure_ascii=False)
        tasks.append(Task(
            task_id=f"bfcl_{i:03d}",
            category="Tool Use",
            difficulty="Medium",
            prompt=prompt,
            gold_answer=gt,
            reasoning_steps=[],
            rubric=["calls_correct_function_with_correct_arguments"],
            evidence=[],
            metadata={"source": "bfcl", "split": "train", "benchmark": "bfcl",
                      "test_category": str(row["test_category"]),
                      "language": str(row["language"]),
                      "tools": _json_field(row["tools"]), "functions": _json_field(row["functions"]),
                      "bfcl_id": str(row["id"])},
        ))
    return tasks


def load_phase1_tasks(n_per_bench: int | None = None) -> list[Task]:
    """I assemble the Phase-1 probe set: five families x `n_per_bench` questions each.
    GSM8K (math) + MATH-500 (hard math, L1) + MMLU-Pro (logic, L1) + FAB (finance,
    heavy-FC L2) + BFCL simple (tool-use, light-FC L2). Default 50 each -> 250 total."""
    if n_per_bench is None:
        from src.config import PHASE1_N_PER_BENCH
        n_per_bench = PHASE1_N_PER_BENCH

    tasks: list[Task] = []
    tasks += load_gsm8k_questions(limit=n_per_bench)
    tasks += load_math500_questions(limit=n_per_bench)
    tasks += load_mmlu_pro_questions(limit=n_per_bench)
    tasks += load_fab_questions()[:n_per_bench]
    tasks += load_bfcl_questions(limit=n_per_bench)
    return tasks


if __name__ == "__main__":
    # Show mini benchmark
    mini = load_tasks()
    print(f"Mini benchmark: {len(mini)} tasks")
    for t in mini:
        print(f"  [{t.task_id}] {t.category:<26} {t.difficulty:<6} {t.prompt[:60]}...")

    # Show FAB public subset
    fab = load_fab_questions()
    print(f"\nFAB public subset: {len(fab)} tasks")
    for t in fab[:5]:
        print(f"  [{t.task_id}] {t.category:<30} {t.difficulty:<6} {t.prompt[:60]}...")
    if len(fab) > 5:
        print(f"  ... and {len(fab) - 5} more")
