import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


DATASET_PATH = Path("eval/datasets/eval_cases.json")
OUTPUT_PATH = Path("eval/outputs/eval_report.json")


def lower_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def approx_equal(a: float | None, b: float | None, tol: float = 1.0) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def parse_coverage(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            numerator = float(left.strip())
            denominator = float(right.strip())
            if denominator == 0:
                return 0.0
            return round(numerator / denominator, 4)
        except (TypeError, ValueError):
            return None

    try:
        return float(text)
    except ValueError:
        return None


def to_serializable(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {k: to_serializable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_serializable(v) for v in value]

    if is_dataclass(value):
        return to_serializable(asdict(value))

    if hasattr(value, "model_dump") and callable(value.model_dump):
        return to_serializable(value.model_dump())

    if hasattr(value, "dict") and callable(value.dict):
        return to_serializable(value.dict())

    if hasattr(value, "__dict__"):
        data = {
            k: v
            for k, v in vars(value).items()
            if not callable(v) and not k.startswith("_")
        }
        return to_serializable(data)

    return str(value)


def normalize_response(response: Any) -> dict:
    data = to_serializable(response)
    if isinstance(data, dict):
        return data
    return {
        "mode": "unknown",
        "items": [],
        "total_calories": None,
        "coverage": 0.0,
        "matched_items": 0,
        "total_items": 0,
        "confidence": None,
        "final_message": str(data),
        "suggestions": [],
    }


def invoke(orchestrator: NutritionOrchestrator, user_input: str) -> dict:
    result = orchestrator.run(user_input)
    normalized = normalize_response(result)
    normalized["_debug_response_type"] = type(result).__name__
    return normalized


def get_mode(response: dict) -> str:
    for key in ["mode", "intent", "response_mode"]:
        value = response.get(key)
        if value:
            return lower_text(value)
    return ""


def get_total_items(response: dict) -> int:
    for key in ["total_items", "item_count", "parsed_items_count", "num_items"]:
        value = safe_int(response.get(key))
        if value is not None:
            return value
    return 0


def get_matched_items(response: dict) -> int:
    for key in ["matched_items", "matched_count", "resolved_items", "accepted_items"]:
        value = safe_int(response.get(key))
        if value is not None:
            return value

    coverage = parse_coverage(response.get("coverage"))
    total_items = get_total_items(response)
    if coverage is not None and total_items > 0:
        return int(round(coverage * total_items))

    return 0


def get_coverage(response: dict) -> float:
    parsed = parse_coverage(response.get("coverage"))
    if parsed is not None:
        return parsed

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    if total_items <= 0:
        return 0.0
    return round(matched_items / total_items, 4)


def get_total_calories(response: dict) -> float | None:
    for key in ["total_calories", "estimated_total_calories", "calories", "total_kcal", "meal_total_calories"]:
        value = safe_float(response.get(key))
        if value is not None:
            return round(value, 2)
    return None


def get_final_message(response: dict) -> str:
    for key in ["final_message", "message", "answer", "response_text"]:
        value = response.get(key)
        if value:
            return str(value).strip()
    return ""


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def _looks_like_empty_guard(msg: str) -> bool:
    return _contains_any(msg, ["type a food query", "type a nutrition question", "example:", "apple 200g", "is avocado healthy"])


def _looks_like_food_only_guard(msg: str) -> bool:
    return _contains_any(msg, ["200g", "grams", "quantity", "try:", "example:"])


def _looks_like_gibberish_guard(msg: str) -> bool:
    return _contains_any(msg, ["clear english food name", "please type", "example:", "apple 200g", "rewrite", "unclear"])


def _looks_like_non_english_guard(msg: str) -> bool:
    return _contains_any(msg, ["english", "in english", "example:", "apple 200g", "is avocado healthy", "please type"])


def _looks_like_quantity_only_guard(msg: str) -> bool:
    return _contains_any(msg, ["food", "include", "food name", "apple 200g", "example:"])


def _looks_like_non_numeric_quantity_guard(msg: str) -> bool:
    return _contains_any(msg, ["digits", "quantity", "apple 200g", "example:"])


def _looks_like_state_total(msg: str) -> bool:
    return _contains_any(msg, ["total", "meal is empty", "current meal", "empty"])


def semantic_guard_match(semantic: str, final_message: str) -> bool:
    msg = lower_text(final_message)

    mapping = {
        "empty": _looks_like_empty_guard,
        "food_only": _looks_like_food_only_guard,
        "gibberish": _looks_like_gibberish_guard,
        "non_english": _looks_like_non_english_guard,
        "quantity_only": _looks_like_quantity_only_guard,
        "non_numeric_quantity": _looks_like_non_numeric_quantity_guard,
        "state_total": _looks_like_state_total,
    }

    fn = mapping.get(semantic)
    if fn is None:
        return True
    return fn(msg)


def evaluate_single_turn(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []
    expected = case["expected"]
    category = case["category"]

    mode = get_mode(response)
    matched_items = get_matched_items(response)
    total_items = get_total_items(response)
    coverage = get_coverage(response)
    total_calories = get_total_calories(response)
    final_message = lower_text(get_final_message(response))

    score = 100.0

    if category == "CAL":
        expected_mode = lower_text(expected.get("mode"))
        if expected_mode and mode != expected_mode:
            errors.append(f"Expected mode={expected_mode}, got {mode}")
            score -= 15

        exp_matched = safe_int(expected.get("matched_items"))
        if exp_matched is not None and matched_items != exp_matched:
            errors.append(f"Expected matched_items={exp_matched}, got {matched_items}")
            score -= 20

        exp_total_items = safe_int(expected.get("total_items"))
        if exp_total_items is not None and total_items != exp_total_items:
            errors.append(f"Expected total_items={exp_total_items}, got {total_items}")
            score -= 20

        exp_coverage = safe_float(expected.get("coverage"))
        if exp_coverage is not None and not approx_equal(coverage, exp_coverage, 0.001):
            errors.append(f"Expected coverage={exp_coverage}, got {coverage}")
            score -= 15

        exp_total_cal = safe_float(expected.get("total_calories"))
        if exp_total_cal is not None and not approx_equal(total_calories, exp_total_cal, 2.0):
            errors.append(f"Expected total_calories≈{exp_total_cal}, got {total_calories}")
            score -= 30

    elif category == "GRD":
        if expected.get("message_non_empty") and not final_message:
            errors.append("Expected non-empty final_message")
            score -= 50

        semantic = expected.get("semantic_guard")
        if semantic and not semantic_guard_match(semantic, final_message):
            errors.append(f"Semantic guard expectation failed for {semantic}, got '{final_message}'")
            score -= 50

    elif category == "MUL":
        expected_mode = lower_text(expected.get("mode"))
        if expected_mode and mode != expected_mode:
            errors.append(f"Expected mode={expected_mode}, got {mode}")
            score -= 15

        exp_matched = safe_int(expected.get("matched_items"))
        if exp_matched is not None and matched_items != exp_matched:
            errors.append(f"Expected matched_items={exp_matched}, got {matched_items}")
            score -= 20

        exp_total_items = safe_int(expected.get("total_items"))
        if exp_total_items is not None and total_items != exp_total_items:
            errors.append(f"Expected total_items={exp_total_items}, got {total_items}")
            score -= 20

        exp_coverage = safe_float(expected.get("coverage"))
        if exp_coverage is not None and not approx_equal(coverage, exp_coverage, 0.001):
            errors.append(f"Expected coverage={exp_coverage}, got {coverage}")
            score -= 15

        exp_total_cal = safe_float(expected.get("total_calories"))
        if exp_total_cal is not None and not approx_equal(total_calories, exp_total_cal, 5.0):
            errors.append(f"Expected total_calories≈{exp_total_cal}, got {total_calories}")
            score -= 30

    elif category == "QA":
        if expected.get("message_non_empty") and not final_message:
            errors.append("Expected non-empty final_message")
            score -= 70

        mode_candidates = [lower_text(x) for x in expected.get("mode_candidates", [])]
        if mode_candidates and mode not in mode_candidates:
            errors.append(f"Expected mode in {mode_candidates}, got {mode}")
            score -= 30

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_multi_turn(case: dict, orchestrator: NutritionOrchestrator) -> tuple[bool, list[str], float, dict]:
    errors = []
    expected = case["expected"]
    category = case["category"]

    last_response = {}
    for step in case["steps"]:
        last_response = invoke(orchestrator, step)

    mode = get_mode(last_response)
    matched_items = get_matched_items(last_response)
    total_calories = get_total_calories(last_response)
    final_message = lower_text(get_final_message(last_response))

    score = 100.0

    if category in {"MEM"}:
        final_mode = lower_text(expected.get("final_mode"))
        if final_mode and mode != final_mode:
            errors.append(f"Expected final_mode={final_mode}, got {mode}")
            score -= 20

        exp_total = safe_float(expected.get("meal_total"))
        if exp_total is not None and not approx_equal(total_calories, exp_total, 5.0):
            errors.append(f"Expected meal_total≈{exp_total}, got {total_calories}")
            score -= 50

        exp_matched = safe_int(expected.get("matched_items"))
        if exp_matched is not None and matched_items < exp_matched:
            errors.append(f"Expected matched_items>={exp_matched}, got {matched_items}")
            score -= 30

    return len(errors) == 0, errors, max(0.0, round(score, 2)), last_response


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"{DATASET_PATH} not found. Run generate_eval_dataset.py first.")

    with DATASET_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    orchestrator = NutritionOrchestrator()

    passed = 0
    failed = 0
    score_sum = 0.0
    failed_cases = []
    category_stats = {}
    detailed_results = []

    for case in cases:
        category = case["category"]
        category_stats.setdefault(category, {"total": 0, "passed": 0, "failed": 0, "score_sum": 0.0})
        category_stats[category]["total"] += 1

        if case["kind"] == "multi_turn":
            ok, errors, score, response = evaluate_multi_turn(case, orchestrator)
        else:
            response = invoke(orchestrator, case["input"])
            ok, errors, score = evaluate_single_turn(case, response)

        score_sum += score
        category_stats[category]["score_sum"] += score

        if ok:
            passed += 1
            category_stats[category]["passed"] += 1
        else:
            failed += 1
            category_stats[category]["failed"] += 1
            failed_cases.append(
                {
                    "case_id": case["case_id"],
                    "category": category,
                    "input": case.get("input", case.get("steps")),
                    "errors": errors,
                }
            )

        detailed_results.append(
            {
                "case_id": case["case_id"],
                "category": category,
                "passed": ok,
                "score": score,
                "expected": case["expected"],
                "response": response,
                "errors": errors,
            }
        )

    total_cases = len(cases)
    pass_rate = round((passed / total_cases) * 100.0, 2) if total_cases else 0.0
    avg_score = round(score_sum / total_cases, 2) if total_cases else 0.0

    report = {
        "dataset_path": str(DATASET_PATH.resolve()),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed,
            "failed_cases": failed,
            "pass_rate": pass_rate,
            "average_score": avg_score,
        },
        "category_breakdown": [],
        "failed_cases": failed_cases,
        "detailed_results": detailed_results,
    }

    for category, stats in sorted(category_stats.items()):
        total = stats["total"]
        report["category_breakdown"].append(
            {
                "category": category,
                "total": total,
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": round((stats["passed"] / total) * 100.0, 2) if total else 0.0,
                "avg_score": round(stats["score_sum"] / total, 2) if total else 0.0,
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("Nutrition Assistant Evaluation Report")
    print("=" * 70)
    print(f"Dataset path    : {DATASET_PATH.resolve()}")
    print(f"Total cases     : {total_cases}")
    print(f"Passed cases    : {passed}")
    print(f"Failed cases    : {failed}")
    print(f"Pass rate       : {pass_rate:.2f}%")
    print(f"Average score   : {avg_score:.2f}%")
    print(f"Report written  : {OUTPUT_PATH.resolve()}")
    print("=" * 70)
    print()
    print("Category breakdown")
    print("=" * 70)
    print(f"{'Category':<10}{'Total':>8}{'Passed':>10}{'Failed':>10}{'Pass Rate':>14}{'Avg Score':>14}")
    print("-" * 70)

    for row in report["category_breakdown"]:
        print(
            f"{row['category']:<10}"
            f"{row['total']:>8}"
            f"{row['passed']:>10}"
            f"{row['failed']:>10}"
            f"{row['pass_rate']:>13.2f}%"
            f"{row['avg_score']:>13.2f}%"
        )

    print("=" * 70)

    if failed_cases:
        print()
        print("Failed cases:")
        for case in failed_cases[:100]:
            print(f"- {case['case_id']} [{case['category']}]:")
            for err in case["errors"]:
                print(f"    * {err}")


if __name__ == "__main__":
    main()