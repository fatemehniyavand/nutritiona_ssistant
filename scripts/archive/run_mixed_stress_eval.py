import json
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


DATASET_PATH = Path("eval/datasets/eval_cases_mixed_stress.json")
OUTPUT_PATH = Path("eval/outputs/eval_report_mixed_stress.json")


MODE_ALIASES = {
    "calorie": "calorie_input",
    "calorie_input": "calorie_input",
    "qa": "nutrition_qa",
    "nutrition_qa": "nutrition_qa",
}


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


def lower_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


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
        "final_message": str(data),
        "items": [],
        "total_calories": None,
        "coverage": 0.0,
        "matched_items": 0,
        "total_items": 0,
    }


def invoke_orchestrator(orchestrator: NutritionOrchestrator, user_input: str) -> dict:
    result = orchestrator.run(user_input)
    normalized = normalize_response(result)
    normalized["_debug_response_type"] = type(result).__name__
    return normalized


def canonical_mode(value: Any) -> str:
    raw = lower_text(value)
    return MODE_ALIASES.get(raw, raw)


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
    coverage = parse_coverage(response.get("coverage"))
    if coverage is not None:
        return coverage

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)

    if total_items <= 0:
        return 0.0
    return round(matched_items / total_items, 4)


def get_total_calories(response: dict) -> float | None:
    for key in [
        "total_calories",
        "estimated_total_calories",
        "calories",
        "total_kcal",
        "meal_total_calories",
    ]:
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


def response_mode(response: dict) -> str:
    for key in ["mode", "intent", "response_mode"]:
        value = response.get(key)
        if value:
            return canonical_mode(value)
    return ""


def evaluate_exact_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    errors = []
    expected = case["expected"]

    expected_mode = canonical_mode(expected.get("mode"))
    actual_mode = response_mode(response)
    if actual_mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {actual_mode or response.get('mode')}")

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)
    total_calories = get_total_calories(response)

    expected_total_items = expected.get("total_items")
    expected_matched_items = expected.get("matched_items")
    expected_coverage = safe_float(expected.get("coverage"))
    expected_total_calories = safe_float(expected.get("total_calories"))

    if total_items != expected_total_items:
        errors.append(f"Expected total_items={expected_total_items}, got {total_items}")

    if matched_items != expected_matched_items:
        errors.append(f"Expected matched_items={expected_matched_items}, got {matched_items}")

    if expected_coverage is not None and not approx_equal(coverage, expected_coverage, tol=0.001):
        errors.append(f"Expected coverage={expected_coverage}, got {coverage}")

    if expected_total_calories is not None and not approx_equal(total_calories, expected_total_calories, tol=1.0):
        errors.append(f"Expected total_calories≈{expected_total_calories}, got {total_calories}")

    return len(errors) == 0, errors


def evaluate_noisy_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    errors = []
    expected = case["expected"]

    expected_mode = canonical_mode(expected.get("mode"))
    actual_mode = response_mode(response)
    if actual_mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {actual_mode or response.get('mode')}")

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)

    expected_total_items = expected.get("total_items")
    matched_items_min = int(expected.get("matched_items_min", 0))
    matched_items_max = int(expected.get("matched_items_max", expected_total_items))
    coverage_min = safe_float(expected.get("coverage_min"), 0.0)
    coverage_max = safe_float(expected.get("coverage_max"), 1.0)

    if total_items != expected_total_items:
        errors.append(f"Expected total_items={expected_total_items}, got {total_items}")

    if not (matched_items_min <= matched_items <= matched_items_max):
        errors.append(f"Expected matched_items in [{matched_items_min}, {matched_items_max}], got {matched_items}")

    if not (coverage_min <= coverage <= coverage_max):
        errors.append(f"Expected coverage in [{coverage_min}, {coverage_max}], got {coverage}")

    return len(errors) == 0, errors


def evaluate_multi_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    errors = []
    expected = case["expected"]

    expected_mode = canonical_mode(expected.get("mode"))
    actual_mode = response_mode(response)
    if actual_mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {actual_mode or response.get('mode')}")

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)

    expected_total_items = int(expected.get("total_items"))
    matched_items_min = int(expected.get("matched_items_min", 0))
    matched_items_max = int(expected.get("matched_items_max", expected_total_items))
    coverage_min = safe_float(expected.get("coverage_min"), 0.0)
    coverage_max = safe_float(expected.get("coverage_max"), 1.0)

    if total_items != expected_total_items:
        errors.append(f"Expected total_items={expected_total_items}, got {total_items}")

    if not (matched_items_min <= matched_items <= matched_items_max):
        errors.append(f"Expected matched_items in [{matched_items_min}, {matched_items_max}], got {matched_items}")

    if not (coverage_min <= coverage <= coverage_max):
        errors.append(f"Expected coverage in [{coverage_min}, {coverage_max}], got {coverage}")

    return len(errors) == 0, errors


def evaluate_ood_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    errors = []
    expected = case["expected"]

    expected_mode = canonical_mode(expected.get("mode"))
    actual_mode = response_mode(response)
    if actual_mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {actual_mode or response.get('mode')}")

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)

    expected_total_items = int(expected.get("total_items"))
    matched_items_min = int(expected.get("matched_items_min", 0))
    matched_items_max = int(expected.get("matched_items_max", 1))
    coverage_min = safe_float(expected.get("coverage_min"), 0.0)
    coverage_max = safe_float(expected.get("coverage_max"), 1.0)

    if total_items != expected_total_items:
        errors.append(f"Expected total_items={expected_total_items}, got {total_items}")

    if not (matched_items_min <= matched_items <= matched_items_max):
        errors.append(f"Expected matched_items in [{matched_items_min}, {matched_items_max}], got {matched_items}")

    if not (coverage_min <= coverage <= coverage_max):
        errors.append(f"Expected coverage in [{coverage_min}, {coverage_max}], got {coverage}")

    return len(errors) == 0, errors


def evaluate_case(case: dict, response: dict) -> tuple[bool, list[str]]:
    category = case.get("category")

    if category == "MIX_EXACT":
        return evaluate_exact_case(case, response)
    if category == "MIX_NOISE":
        return evaluate_noisy_case(case, response)
    if category == "MIX_MULTI":
        return evaluate_multi_case(case, response)
    if category == "MIX_OOD":
        return evaluate_ood_case(case, response)

    return False, [f"Unknown category: {category}"]


def category_score(case: dict, response: dict) -> float:
    category = case.get("category")

    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)

    if category == "MIX_EXACT":
        expected_total = safe_float(case["expected"].get("total_calories"))
        actual_total = get_total_calories(response)
        score = 100.0
        if total_items != 1:
            score -= 40
        if matched_items != 1:
            score -= 40
        if expected_total is not None and actual_total is not None and not approx_equal(expected_total, actual_total, tol=1.0):
            score -= 20
        return max(0.0, score)

    if category == "MIX_NOISE":
        return round(min(100.0, coverage * 100.0), 2)

    if category == "MIX_MULTI":
        if total_items <= 0:
            return 0.0
        parse_score = 50.0 if total_items == int(case["expected"]["total_items"]) else 0.0
        match_score = min(50.0, (matched_items / total_items) * 50.0)
        return round(parse_score + match_score, 2)

    if category == "MIX_OOD":
        if matched_items == 0:
            return 100.0
        if matched_items == 1 and coverage <= 1.0:
            return 60.0
        return 30.0

    return 0.0


def make_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "score_sum": 0.0,
        "matched_items_sum": 0,
        "total_items_sum": 0,
        "coverage_sum": 0.0,
    }


def summarize_category(category: str, stats: dict[str, Any]) -> dict[str, Any]:
    total = stats["total"]
    passed = stats["passed"]
    failed = stats["failed"]
    score_sum = stats["score_sum"]
    matched_items_sum = stats["matched_items_sum"]
    total_items_sum = stats["total_items_sum"]
    coverage_sum = stats["coverage_sum"]

    pass_rate = round((passed / total) * 100.0, 2) if total else 0.0
    avg_score = round(score_sum / total, 2) if total else 0.0
    avg_coverage = round(coverage_sum / total, 4) if total else 0.0
    item_recovery = round((matched_items_sum / total_items_sum) * 100.0, 2) if total_items_sum else 0.0

    return {
        "category": category,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "avg_coverage": avg_coverage,
        "item_recovery_rate": item_recovery,
    }


def print_report(dataset_path: Path, output_path: Path, overall: dict[str, Any], category_rows: list[dict[str, Any]], failed_cases: list[dict[str, Any]]) -> None:
    print("=" * 70)
    print("Nutrition Assistant Mixed Stress Evaluation Report")
    print("=" * 70)
    print(f"Dataset path    : {dataset_path.resolve()}")
    print(f"Total cases     : {overall['total_cases']}")
    print(f"Passed cases    : {overall['passed_cases']}")
    print(f"Failed cases    : {overall['failed_cases']}")
    print(f"Pass rate       : {overall['pass_rate']:.2f}%")
    print(f"Average score   : {overall['average_score']:.2f}%")
    print(f"Average coverage: {overall['average_coverage']:.4f}")
    print(f"Item recovery   : {overall['item_recovery_rate']:.2f}%")
    print(f"Report written  : {output_path.resolve()}")
    print("=" * 70)
    print()
    print("Category breakdown")
    print("=" * 70)
    print(
        f"{'Category':<14}"
        f"{'Total':>8}"
        f"{'Passed':>10}"
        f"{'Failed':>9}"
        f"{'Pass Rate':>14}"
        f"{'Avg Score':>13}"
        f"{'Avg Cov':>10}"
        f"{'Recovery':>11}"
    )
    print("-" * 70)
    for row in category_rows:
        print(
            f"{row['category']:<14}"
            f"{row['total']:>8}"
            f"{row['passed']:>10}"
            f"{row['failed']:>9}"
            f"{row['pass_rate']:>13.2f}%"
            f"{row['avg_score']:>12.2f}%"
            f"{row['avg_coverage']:>10.4f}"
            f"{row['item_recovery_rate']:>10.2f}%"
        )
    print("=" * 70)

    if failed_cases:
        print()
        print("Failed cases:")
        for case in failed_cases[:20]:
            print(f"- {case['case_id']} [{case['category']}]")
            print(f"    Input: {case['input']}")
            for err in case["errors"]:
                print(f"    * {err}")


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    with DATASET_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset is empty or invalid.")

    orchestrator = NutritionOrchestrator()

    category_stats: dict[str, dict[str, Any]] = defaultdict(make_stats)
    failed_cases = []
    detailed_results = []

    total_cases = len(cases)
    passed_cases = 0
    failed_count = 0
    score_sum = 0.0
    coverage_sum = 0.0
    matched_items_sum = 0
    total_items_sum = 0

    print("=" * 70)
    print("Running MIXED STRESS evaluation")
    print("=" * 70)
    print(f"Using dataset: {DATASET_PATH.resolve()}")
    print("=" * 70)

    for idx, case in enumerate(cases, start=1):
        user_input = case["input"]
        category = case["category"]
        case_id = case["case_id"]

        response = invoke_orchestrator(orchestrator, user_input)

        passed, errors = evaluate_case(case, response)
        score = category_score(case, response)
        coverage = get_coverage(response)
        matched_items = get_matched_items(response)
        total_items = get_total_items(response)

        score_sum += score
        coverage_sum += coverage
        matched_items_sum += matched_items
        total_items_sum += total_items

        stats = category_stats[category]
        stats["total"] += 1
        stats["score_sum"] += score
        stats["coverage_sum"] += coverage
        stats["matched_items_sum"] += matched_items
        stats["total_items_sum"] += total_items

        if passed:
            passed_cases += 1
            stats["passed"] += 1
        else:
            failed_count += 1
            stats["failed"] += 1
            failed_cases.append(
                {
                    "case_id": case_id,
                    "category": category,
                    "input": user_input,
                    "errors": errors,
                    "response_preview": {
                        "mode": response_mode(response),
                        "matched_items": matched_items,
                        "total_items": total_items,
                        "coverage": coverage,
                        "total_calories": get_total_calories(response),
                        "final_message": get_final_message(response),
                        "response_type": response.get("_debug_response_type"),
                    },
                }
            )

        detailed_results.append(
            {
                "case_id": case_id,
                "category": category,
                "input": user_input,
                "passed": passed,
                "score": round(score, 2),
                "errors": errors,
                "response_summary": {
                    "mode": response_mode(response),
                    "total_items": total_items,
                    "matched_items": matched_items,
                    "coverage": coverage,
                    "total_calories": get_total_calories(response),
                    "final_message": get_final_message(response),
                    "response_type": response.get("_debug_response_type"),
                },
                "expected": case.get("expected"),
                "meta": case.get("meta", {}),
            }
        )

        if idx % 25 == 0 or idx == total_cases:
            print(f"Progress: {idx}/{total_cases} | passed={passed_cases} | failed={failed_count}")

    category_rows = [summarize_category(category, stats) for category, stats in sorted(category_stats.items())]

    average_score = round(score_sum / total_cases, 2) if total_cases else 0.0
    pass_rate = round((passed_cases / total_cases) * 100.0, 2) if total_cases else 0.0
    average_coverage = round(coverage_sum / total_cases, 4) if total_cases else 0.0
    item_recovery_rate = round((matched_items_sum / total_items_sum) * 100.0, 2) if total_items_sum else 0.0

    report = {
        "report_name": "mixed_stress_eval",
        "dataset_path": str(DATASET_PATH),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_count,
            "pass_rate": pass_rate,
            "average_score": average_score,
            "average_coverage": average_coverage,
            "item_recovery_rate": item_recovery_rate,
        },
        "category_breakdown": category_rows,
        "failed_cases": failed_cases,
        "detailed_results": detailed_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print_report(DATASET_PATH, OUTPUT_PATH, report["summary"], category_rows, failed_cases)


if __name__ == "__main__":
    main()