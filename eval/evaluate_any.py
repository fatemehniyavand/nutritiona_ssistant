import argparse
import asyncio
import inspect
import json
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


PASS_THRESHOLD = 0.80
EPSILON = 1e-9


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).lower().strip()


def tokenize(text: str) -> set:
    return set(re.findall(r"[a-zA-Z]+", normalize_text(text)))


def token_similarity(a: str, b: str) -> float:
    a_tokens = tokenize(a)
    b_tokens = tokenize(b)
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def to_plain_data(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: to_plain_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_plain_data(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return {k: to_plain_data(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return obj


def extract_answer_and_mode(raw: Any) -> Tuple[str, str, Dict[str, Any]]:
    data = to_plain_data(raw)

    if isinstance(data, str):
        return data, "", {"raw": data}

    if not isinstance(data, dict):
        return str(data), "", {"raw": str(data)}

    possible_answer_keys = [
        "answer",
        "final_answer",
        "final_message",
        "message",
        "content",
        "response",
        "response_text",
        "text",
    ]

    answer_parts = []
    for key in possible_answer_keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            answer_parts.append(value)

    if not answer_parts:
        answer_parts.append(json.dumps(data, ensure_ascii=False))

    mode = (
        data.get("mode")
        or data.get("intent")
        or data.get("detected_mode")
        or data.get("expected_intent")
        or ""
    )

    return "\n".join(answer_parts), str(mode), data


def load_orchestrator():
    try:
        from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
        return NutritionOrchestrator()
    except Exception as exc:
        raise RuntimeError(
            "Could not import or initialize NutritionOrchestrator. "
            "Run with PYTHONPATH=. and check src/application/orchestrators/nutrition_orchestrator.py"
        ) from exc


async def call_orchestrator(orchestrator: Any, user_input: str) -> Any:
    method_names = [
        "handle_message",
        "process_message",
        "run",
        "answer",
        "ask",
        "execute",
        "__call__",
    ]

    last_error = None

    for name in method_names:
        method = getattr(orchestrator, name, None)
        if method is None:
            continue

        try:
            result = method(user_input)
            if inspect.isawaitable(result):
                result = await result
            return result
        except TypeError as exc:
            last_error = exc
            continue

    raise RuntimeError(f"No compatible orchestrator method found. Last error: {last_error}")


def contains_any(text: str, phrases: List[str]) -> bool:
    t = normalize_text(text)
    return any(normalize_text(p) in t for p in phrases)


def contains_all(text: str, phrases: List[str]) -> bool:
    t = normalize_text(text)
    return all(normalize_text(p) in t for p in phrases)


def contains_none(text: str, phrases: List[str]) -> bool:
    t = normalize_text(text)
    return all(normalize_text(p) not in t for p in phrases)


def behavior_checks(answer: str, case: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    rules = case.get("behavior_rules", {})
    score_parts = []
    passed = []
    failed = []

    def add_check(name: str, ok: bool, weight: float = 1.0):
        score_parts.append((weight, ok))
        if ok:
            passed.append(name)
        else:
            failed.append(name)

    must_contain_any = rules.get("must_contain_any", [])
    if must_contain_any:
        add_check("must_contain_any", contains_any(answer, must_contain_any), 1.0)

    must_contain_all = rules.get("must_contain_all", [])
    if must_contain_all:
        add_check("must_contain_all", contains_all(answer, must_contain_all), 1.2)

    must_not_contain = rules.get("must_not_contain", [])
    if must_not_contain:
        add_check("must_not_contain", contains_none(answer, must_not_contain), 1.2)

    if rules.get("must_ask_clarification"):
        clarification_markers = [
            "clarify", "could you specify", "which food", "what food",
            "more information", "more details", "please provide", "?"
        ]
        add_check("must_ask_clarification", contains_any(answer, clarification_markers), 1.5)

    if rules.get("must_refuse_ood"):
        ood_markers = [
            "outside", "not related to nutrition", "nutrition scope",
            "food", "diet", "calories", "nutrition"
        ]
        add_check("must_refuse_ood_or_redirect", contains_any(answer, ood_markers), 1.5)

    if rules.get("must_correct_misinformation"):
        correction_markers = [
            "not true", "not accurate", "myth", "does not", "cannot",
            "not always", "depends", "evidence", "unsafe"
        ]
        add_check("must_correct_misinformation", contains_any(answer, correction_markers), 1.5)

    if rules.get("must_not_calculate_calories"):
        calorie_calc_markers = [
            "estimated calories", "total calories", "kcal per 100 g",
            "matched food", "meal memory"
        ]
        add_check("must_not_calculate_calories", contains_none(answer, calorie_calc_markers), 1.3)

    if rules.get("must_mention_uncertainty"):
        uncertainty_markers = [
            "depends", "may", "can", "usually", "context", "health status",
            "individual", "not always"
        ]
        add_check("must_mention_uncertainty", contains_any(answer, uncertainty_markers), 1.0)

    if not score_parts:
        return 1.0, passed, failed

    total_weight = sum(w for w, _ in score_parts)
    earned = sum(w for w, ok in score_parts if ok)
    return earned / total_weight, passed, failed


def evaluate_case(answer: str, mode: str, case: Dict[str, Any]) -> Dict[str, Any]:
    failures = []
    details = {}

    expected_intent = case.get("expected_intent")
    if expected_intent:
        if isinstance(expected_intent, list):
            intent_ok = mode in expected_intent or not mode
        else:
            intent_ok = mode == expected_intent or not mode
        details["intent_ok"] = intent_ok
        if not intent_ok:
            failures.append(f"Expected intent {expected_intent}, got {mode}")

    expected_contains_any = case.get("expected_contains_any", [])
    if expected_contains_any:
        ok = contains_any(answer, expected_contains_any)
        details["expected_contains_any_ok"] = ok
        if not ok:
            failures.append("Answer missed expected keywords/phrases")

    should_not_contain = case.get("should_not_contain", [])
    if should_not_contain:
        ok = contains_none(answer, should_not_contain)
        details["should_not_contain_ok"] = ok
        if not ok:
            failures.append("Answer contained forbidden phrase")

    ref = case.get("reference_answer", "")
    min_sim = float(case.get("min_similarity_to_reference", 0.0))
    sim = token_similarity(answer, ref) if ref else 1.0
    details["similarity_to_reference"] = round(sim, 4)

    if ref and min_sim > 0:
        ok = sim + EPSILON >= min_sim
        details["similarity_ok"] = ok
        if not ok:
            details["similarity_warning"] = f"Similarity low: {sim:.3f} < {min_sim:.3f}"

    behavior_score, behavior_passed, behavior_failed = behavior_checks(answer, case)
    details["behavior_score"] = round(behavior_score, 4)
    details["behavior_passed"] = behavior_passed
    details["behavior_failed"] = behavior_failed

    if behavior_score + EPSILON < PASS_THRESHOLD:
        failures.append(f"Behavior score too low: {behavior_score:.3f} < {PASS_THRESHOLD:.3f}")

    component_scores = []

    if "expected_contains_any_ok" in details:
        component_scores.append(1.0 if details["expected_contains_any_ok"] else 0.0)

    if "should_not_contain_ok" in details:
        component_scores.append(1.0 if details["should_not_contain_ok"] else 0.0)

    if ref and min_sim > 0:
        component_scores.append(min(sim / min_sim, 1.0))

    component_scores.append(behavior_score)

    final_score = sum(component_scores) / len(component_scores)
    passed = len(failures) == 0

    return {
        "passed": passed,
        "score": round(final_score, 4),
        "failures": failures,
        "details": details,
    }


async def main_async(dataset_path: Path) -> None:
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    orchestrator = load_orchestrator()

    results = []
    passed_count = 0

    for case in cases:
        raw = await call_orchestrator(orchestrator, case["input"])
        answer, mode, raw_data = extract_answer_and_mode(raw)

        evaluation = evaluate_case(answer, mode, case)
        if evaluation["passed"]:
            passed_count += 1

        results.append({
            "id": case.get("id"),
            "category": case.get("category"),
            "case_type": case.get("case_type"),
            "topic": case.get("topic"),
            "input": case.get("input"),
            "expected_intent": case.get("expected_intent"),
            "detected_mode": mode,
            "passed": evaluation["passed"],
            "score": evaluation["score"],
            "failures": evaluation["failures"],
            "details": evaluation["details"],
            "answer": answer,
            "raw_response": raw_data,
        })

    total = len(cases)
    failed_count = total - passed_count
    pass_rate = passed_count / total * 100 if total else 0.0

    by_category = {}
    for r in results:
        cat = r.get("category") or "UNKNOWN"
        by_category.setdefault(cat, {"total": 0, "passed": 0, "failed": 0})
        by_category[cat]["total"] += 1
        if r["passed"]:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1

    by_case_type = {}
    for r in results:
        ct = r.get("case_type") or "UNKNOWN"
        by_case_type.setdefault(ct, {"total": 0, "passed": 0, "failed": 0})
        by_case_type[ct]["total"] += 1
        if r["passed"]:
            by_case_type[ct]["passed"] += 1
        else:
            by_case_type[ct]["failed"] += 1

    report = {
        "dataset_path": str(dataset_path.resolve()),
        "total_cases": total,
        "passed_cases": passed_count,
        "failed_cases": failed_count,
        "pass_rate": round(pass_rate, 2),
        "pass_threshold": PASS_THRESHOLD,
        "category_breakdown": by_category,
        "case_type_breakdown": by_case_type,
        "failed_cases": [r for r in results if not r["passed"]],
        "all_results": results,
    }

    output_path = Path("eval/outputs/eval_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Nutrition Assistant Evaluation Report")
    print("=" * 70)
    print(f"Dataset path    : {dataset_path.resolve()}")
    print(f"Total cases     : {total}")
    print(f"Passed cases    : {passed_count}")
    print(f"Failed cases    : {failed_count}")
    print(f"Pass rate       : {pass_rate:.2f}%")
    print(f"Report written  : {output_path.resolve()}")
    print("=" * 70)

    print("\nCategory breakdown")
    print("=" * 70)
    print(f"{'Category':<24}{'Total':>8}{'Passed':>10}{'Failed':>10}{'Pass Rate':>12}")
    print("-" * 70)
    for cat, stats in by_category.items():
        rate = stats["passed"] / stats["total"] * 100
        print(f"{cat:<24}{stats['total']:>8}{stats['passed']:>10}{stats['failed']:>10}{rate:>11.2f}%")
    print("=" * 70)

    print("\nCase type breakdown")
    print("=" * 70)
    print(f"{'Case Type':<24}{'Total':>8}{'Passed':>10}{'Failed':>10}{'Pass Rate':>12}")
    print("-" * 70)
    for ct, stats in by_case_type.items():
        rate = stats["passed"] / stats["total"] * 100
        print(f"{ct:<24}{stats['total']:>8}{stats['passed']:>10}{stats['failed']:>10}{rate:>11.2f}%")
    print("=" * 70)

    if failed_count:
        print("\nFailed case examples")
        print("=" * 70)
        for r in [x for x in results if not x["passed"]][:10]:
            print(f"- {r['id']} | {r.get('case_type')} | score={r['score']}")
            print(f"  Input   : {r['input']}")
            print(f"  Failure : {r['failures']}")
            print(f"  Answer  : {r['answer'][:300].replace(chr(10), ' ')}")
        print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_path", type=Path)
    args = parser.parse_args()

    if not args.dataset_path.exists():
        print(f"Dataset not found: {args.dataset_path}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main_async(args.dataset_path))


if __name__ == "__main__":
    main()
