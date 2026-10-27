"""
build_mechanism_levels.py
=========================
Level-2 / Level-3 distillation of the EGTE error bank (re-anchored 2026-10-21 RSI loop).

Lifts the level-1 instance mechanisms emitted by ``build_behavior_leaves.py``
(``experiments/l0_distill_v1/relabeled_<family>.jsonl``) up two levels:

  L2 (benchmark-level): cluster ONE solver model's instance mechanisms (across the whole
      family) into a SMALL number of benchmark-level classes by their underlying wrong
      operation, and emit ONE answer-free mechanism + check_procedure + trigger per class.
      PER-MODEL: each model keeps its OWN error bank (a strong model's rare/subtle errors
      differ from a weak model's frequent/blunt ones — pooling them dilutes precision and
      lets another model's mechanism false-eliminate this model's correct moves).
  L3 (cross-benchmark): classify each L2 mechanism into EXACTLY ONE of the 7 canonical
      ANSWER-FREE wrong-execution archetypes. The 7 archetypes are the SHARED, model-agnostic
      vocabulary; only the concrete L1/L2 mechanisms are per-model. Test-time CHECK and
      REVIEW consume ONLY this level.

Canonical L3 archetypes (frozen): constraint_blind / descriptor_conflation /
  memory_substitution / procedure_truncation / sign_normalization_slip /
  retrieval_abort / format_nonconformance.

Pilot (2026-10-21): glm-5.3 gpqa (one model, full family) end-to-end.

Reproducibility: deterministic inputs, temperature = 0, per-model bucketing. One command:
  python3 src/build_mechanism_levels.py --model glm-5.3 --family gpqa
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _force_no_proxy() -> None:
    """Bypass the macOS system proxy (127.0.0.1:3213) which stalls the openai SDK."""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


_load_dotenv()
_force_no_proxy()

from src import config  # noqa: E402
from src.agent import HuggingFaceAgent  # noqa: E402

SRC_BANK = ROOT / "experiments" / "error_taxonomy_v2" / "wrong_bank.jsonl"
OUT_DIR = ROOT / "experiments" / "l0_distill_v1"
MERGE_MODEL = "deepseek-v4-flash"  # model used to RUN the merge/archive calls

MERGE_CONTENT_MARGIN = int(os.getenv("L2_CONTENT_MARGIN", "4096"))
MERGE_THINKING_BUDGET = int(os.getenv("L2_THINKING_BUDGET", "4096"))

# ---- frozen L3 archetype vocabulary (answer-free, cross-benchmark) ----
ARCHETYPES = {
    "constraint_blind": (
        "constraint-blind decimation",
        "forecasts the outcome from a partial/local feature (central-atom geometry, a "
        "self-drawn fragment, one symmetric case) while dropping a decisive hidden "
        "constraint (full 3D conformation, mirror/inversion symmetry, equivalence "
        "classes, atom/conservation balance).",
    ),
    "descriptor_conflation": (
        "descriptor/label conflation",
        "maps the correct structure or relationship onto the wrong label, or swaps two "
        "distinct notions (option letter <-> structure, geometry <-> descriptor-set, "
        "kinetic <-> thermodynamic, action-verb direction).",
    ),
    "memory_substitution": (
        "memorized-fact substitution",
        "answers from a remembered fact or citation instead of running the first-principles "
        "procedure on THIS instance.",
    ),
    "procedure_truncation": (
        "procedure truncation / omission",
        "omits a reaction step, reagent order, an atom/Degree-of-Unsaturation conservation "
        "constraint, or the enumerate-all-and-sum requirement.",
    ),
    "sign_normalization_slip": (
        "sign / normalization slip",
        "applies the wrong sign in a formula, wrong log zero-point or scale, or cancels a "
        "reference baseline that must stay.",
    ),
    "retrieval_abort": (
        "retrieval-abort",
        "abandons first-principles derivation when retrieval/recognition confidence is low.",
    ),
    "format_nonconformance": (
        "format / precision non-conformance",
        "reports a non-committal or rounded standalone number instead of honoring the "
        "requested option letter or numeric precision.",
    ),
}

MERGE_SYSTEM = (
    "You are the DISTILLATION role (level 2, benchmark-level) of an Error-Guided "
    "Test-Time Elimination (EGTE) evaluator. Below are instance-level wrong-operation "
    "mechanisms from ONE solver model on the SAME benchmark family. Cluster them into a "
    "SMALL number (aim for <=8, never more than 10) of benchmark-level classes by their "
    "UNDERLYING wrong operation — merge mechanisms that share the same faulty verb, even "
    "when they come from different questions. For EACH class emit ONE answer-free "
    "mechanism (a verb phrase generalizable to any question of that class), a differential "
    "gold-free check_procedure, and a gold-free trigger (question-type + committed-answer "
    "signature). Assign every input mechanism to exactly one class. Do NOT name any "
    "molecule, compound, number, option letter, or answer text. Return JSON only."
)


def build_merge_prompt(rows: list[dict]) -> str:
    lines = []
    for i, r in enumerate(rows, 1):
        lines.append(f"M{i} [{r['task_id']}]: {r['mechanism']}")
    return (
        "Instance-level mechanisms (cluster + merge these):\n"
        + "\n".join(lines)
        + "\n\nReturn ONE JSON object whose KEYS are short class labels, each VALUE an "
        "object:\n"
        "{\n"
        '  "<class_label>": {\n'
        '    "mechanism": "<answer-free benchmark-level wrong OPERATION, verb phrase>",\n'
        '    "check_procedure": "<differential gold-free self-check, no correct option named>",\n'
        '    "trigger": "<gold-free execution signature: question type + committed answer>",\n'
        '    "members": ["M1", "M3"]\n'
        "  }\n"
        "}\n"
        "Every input M# must appear in exactly one class's members list. Output ONLY the "
        "JSON object, no prose."
    )


MAP_SYSTEM = (
    "You are the ARCHIVER role (level 3, cross-benchmark class) of an Error-Guided "
    "Test-Time Elimination (EGTE) evaluator. Classify the given benchmark-level wrong-"
    "operation mechanism into EXACTLY ONE of the 7 answer-free wrong-execution archetypes "
    "listed below. Return the archetype id and a one-line rationale. JSON only."
)


def build_map_prompt(mechanism: str) -> str:
    arche = "\n".join(
        f"- {aid}: {name} — {desc}" for aid, (name, desc) in ARCHETYPES.items()
    )
    return (
        "Archetypes:\n"
        f"{arche}\n\n"
        "Benchmark-level mechanism to classify:\n"
        f"{mechanism}\n\n"
        'Return ONE JSON object: {"archetype_id": "<one id from the list>", '
        '"rationale": "<one line>"}. Output ONLY the JSON object.'
    )


def _extract_json(content: str):
    if not content:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)
    else:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            content = m.group(0)
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _call(entry: dict, system: str, user: str, max_tokens: int):
    agent = HuggingFaceAgent(
        model=entry["model"], token=entry.get("api_key"),
        base_url=entry["base_url"], max_tokens=max_tokens, temperature=0.0,
        seed=None, enable_thinking=entry.get("enable_thinking"),
        thinking_budget=MERGE_THINKING_BUDGET, content_margin=MERGE_CONTENT_MARGIN)
    content, reasoning, info = agent._call_llm_text(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}])
    return content, info


FREEZE_SYSTEM = (
    "You are the DISTILLER role (level 3, answer-free) of an Error-Guided Test-Time "
    "Elimination (EGTE) system. Freeze a benchmark-level error class into a concise, "
    "reusable critic entry: a past-participle 'suspicion' clause plus one de-identified generic "
    "example. Do NOT name any molecule, compound, number, option letter, dataset, or "
    "answer text -- the entry must be reusable on ANY question. Return JSON only."
)


def build_freeze_prompt(rec: dict) -> str:
    l3 = rec.get("level3", {})
    name = l3.get("archetype_name", "")
    return (
        "Archetype: " + name + "\n"
        "Fault mechanism: " + rec.get("mechanism", "") + "\n"
        "Trigger signature: " + rec.get("trigger", "") + "\n"
        "Self-check procedure: " + rec.get("check_procedure", "") + "\n\n"
        "Return ONE JSON object:\n"
        "{\n"
        '  "definition": "<short PAST-PARTICIPLE clause (must START with an -ed/-en verb, '
        "e.g. 'conflated the target category with a related but distinct descriptor'>\",\n"
        '  "examples": ["<one de-identified generic scenario, no names/numbers/answers>"]\n'
        "}\n"
        "Output ONLY the JSON object."
    )


def _freeze_classes(results, model):
    """Freeze each L2/L3 class into answer-free level-3 bank entries (per-model).

    Returns a list of 6-field entry dicts (id / name / definition / trigger /
    check_procedure / examples) plus a 'family' provenance tag. ``definition`` is the
    past-participle 'you may have ...' suspicion clause; ``examples`` are de-identified
    and human-read-only (never injected into the solver). The critic later renders ONLY
    name + definition + check_procedure (trigger is its retrieval key).
    """
    entry = config.PHASE1_MODELS[MERGE_MODEL]
    bank = []
    for rec in results:
        l3 = rec.get("level3", {})
        aid = l3.get("archetype_id", "")
        name = l3.get("archetype_name", "")
        if not aid:
            continue
        definition = rec.get("mechanism", "")  # fallback if freeze step fails
        examples = []
        try:
            content, _ = _call(entry, FREEZE_SYSTEM, build_freeze_prompt(rec), max_tokens=512)
            fobj = _extract_json(content) or {}
        except Exception:
            fobj = {}
        if fobj.get("definition"):
            definition = fobj["definition"]
        if isinstance(fobj.get("examples"), list):
            examples = [str(e) for e in fobj["examples"] if str(e).strip()]
        bank.append({
            "id": aid,
            "name": name,
            "definition": definition,
            "trigger": rec.get("trigger", ""),
            "check_procedure": rec.get("check_procedure", ""),
            "examples": examples,
            "family": rec.get("family", ""),
        })
    return bank


def _write_bank(bank, model, family, out_dir):
    bank_out = out_dir / f"level3_bank_{model}.json"
    payload = {
        "version": "level3_bank_v2",
        "family": family,
        "solver_model": model,
        "n_entries": len(bank),
        "entries": bank,
    }
    with open(bank_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[written] {bank_out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="gpqa")
    ap.add_argument("--bank", default=str(SRC_BANK),
                    help="wrong-bank JSONL to read (default: the error_taxonomy_v2 bank)")
    ap.add_argument("--model", default="glm-5.3", help="solver model whose bank to distill "
                    "(per-model: each model keeps its OWN bank)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--from-levels", default=None,
                    help="skip merge/map; freeze level3_bank from an existing "
                         "mechanism_levels_{model}_{family}.json path")
    ap.add_argument("--no-freeze", action="store_true",
                    help="skip the freeze+bank write (run merge/map only; used as a "
                         "per-family step before a cross-family --merge-families bank)")
    ap.add_argument("--merge-families", default=None,
                    help="comma-separated families whose existing "
                         "mechanism_levels_{model}_{family}.json files are frozen and "
                         "concatenated into ONE cross-benchmark level3_bank_{model}.json")
    args = ap.parse_args()

    if args.merge_families:
        families = [f.strip() for f in args.merge_families.split(",") if f.strip()]
        bank = []
        for fam in families:
            path = OUT_DIR / f"mechanism_levels_{args.model}_{fam}.json"
            data = json.load(open(path, encoding="utf-8"))
            for rec in data.get("classes", []):
                rec["family"] = fam
            bank += _freeze_classes(data.get("classes", []), args.model)
        _write_bank(bank, args.model, "cross", OUT_DIR)
        counts = {}
        for e in bank:
            counts[e["id"]] = counts.get(e["id"], 0) + 1
        print(f"[merge] {len(bank)} entries across {families} -> "
              f"archetype counts: {counts}")
        return

    if args.from_levels:
        data = json.load(open(args.from_levels, encoding="utf-8"))
        fam = data.get("family", args.family)
        for rec in data.get("classes", []):
            rec["family"] = fam
        if not args.no_freeze:
            _write_bank(_freeze_classes(data.get("classes", []),
                                        data.get("solver_model", args.model)),
                        data.get("solver_model", args.model), fam, OUT_DIR)
        return

    # L1 records keyed by (model, family). Each model's rows may share the same task_id
    # only if it erred on the same question in multiple bank entries (rare at present).
    rows = [json.loads(l) for l in open(args.bank, encoding="utf-8")]
    rows = [r for r in rows if r.get("family") == args.family
            and r.get("model") == args.model]

    # Join the L1 mechanism text onto each row from the relabeled file.
    l1_path = ROOT / "experiments" / "l0_distill_v1" / f"relabeled_{args.family}.jsonl"
    l1 = {(r.get("model"), r["task_id"]): r for r in
          [json.loads(l) for l in open(l1_path, encoding="utf-8")]}
    # NOTE: multiple bank rows can share a task_id (a model may err on the same prompt in
    # several collected samples); we merge by task_id here to recover one mechanism each.
    mech_rows = []
    dropped_contamination = []
    for r in rows:
        rec = l1.get((r.get("model"), r["task_id"]))
        mech = (rec.get("mechanism") or "") if rec else ""
        if not (rec and rec.get("parse_ok") and mech):
            continue
        # Data-quality gate: distill marks a wrong_bank row whose final_answer actually
        # equals gold as "no_erroneous_operation". It is NOT a real error, so it must not
        # enter the error bank (else the cluster step invents a fake class for it).
        if "no erroneous operation" in mech.lower():
            dropped_contamination.append(r["task_id"])
            continue
        mech_rows.append({
            "task_id": r["task_id"],
            "problem_class": rec.get("problem_class", ""),
            "mechanism": mech,
            "final_answer": r.get("final_answer", ""),
            "gold_answer": r.get("gold_answer", ""),
        })
    print(f"[load] model={args.model} family={args.family} -> {len(mech_rows)} mechanisms "
          f"(dropped {len(dropped_contamination)} non-error rows: "
          f"{sorted(set(dropped_contamination))})")

    entry = config.PHASE1_MODELS[MERGE_MODEL]

    content, info = _call(entry, MERGE_SYSTEM, build_merge_prompt(mech_rows),
                          max_tokens=4096)
    classes = _extract_json(content) or {}
    print(f"[cluster] raw parse -> {len(classes)} classes "
          f"(finish_reason={getattr(info, 'finish_reason', None)})")

    results = []
    for label, c in classes.items():
        if not isinstance(c, dict):
            continue
        members = c.get("members", [])
        member_tasks = []
        for mi in members:
            idx = int(re.sub(r"\D", "", str(mi)) or 0) - 1
            if 0 <= idx < len(mech_rows):
                member_tasks.append(mech_rows[idx]["task_id"])
        rec = {
            "class_label": label,
            "mechanism": c.get("mechanism", ""),
            "check_procedure": c.get("check_procedure", ""),
            "trigger": c.get("trigger", ""),
            "members": members,
            "member_tasks": member_tasks,
        }
        if rec["mechanism"]:
            mcontent, _ = _call(entry, MAP_SYSTEM, build_map_prompt(rec["mechanism"]),
                                max_tokens=512)
            l3 = _extract_json(mcontent) or {}
            aid = l3.get("archetype_id", "")
            rec["level3"] = {
                "archetype_id": aid,
                "archetype_name": ARCHETYPES.get(aid, ("", ""))[0] if aid in ARCHETYPES else "",
                "rationale": l3.get("rationale", ""),
                "parse_ok": bool(l3),
            }
        else:
            rec["level3"] = {"archetype_id": "", "archetype_name": "", "rationale": "",
                             "parse_ok": False}
        results.append(rec)

    results.sort(key=lambda r: (-len(r["members"]), r["class_label"]))

    out = args.out or (OUT_DIR / f"mechanism_levels_{args.model}_{args.family}.json")
    payload = {
        "version": "l2_l3_pilot_v2",
        "family": args.family,
        "solver_model": args.model,
        "merge_model": entry["model"],
        "n_instances": len(mech_rows),
        "dropped_contamination": sorted(set(dropped_contamination)),
        "n_classes": len(results),
        "archetypes": {aid: name for aid, (name, _) in ARCHETYPES.items()},
        "classes": results,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    for rec in results:
        rec["family"] = args.family
    if not args.no_freeze:
        _write_bank(_freeze_classes(results, args.model), args.model, args.family, OUT_DIR)

    print("\n" + "=" * 80)
    for r in results:
        l3 = r["level3"]
        print(f"[{r['class_label']}] n={len(r['members'])} "
              f"-> {l3.get('archetype_id')}")
        print(f"  members: {', '.join(r['member_tasks'])}")
        print(f"  L2: {r['mechanism'][:120]}")
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
