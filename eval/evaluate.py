import json
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


DATASET_PATH = Path("eval/datasets/eval_cases.json")
OUTPUT_PATH = Path("eval/outputs/eval_report.json")


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    if is_dataclass(value):
        return make_json_safe(asdict(value))
    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump())
    if hasattr(value, "__dict__"):
        return make_json_safe(value.__dict__)
    return str(value)


def parse_coverage(value: Any):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip()
        if "/" in value:
            try:
                a, b = value.split("/", 1)
                return float(a) / float(b)
            except Exception:
                return None
        try:
            return float(value)
        except Exception:
            return None

    return None


def extract_text_from_turn(turn: Any) -> str:
    if isinstance(turn, str):
        return turn

    if isinstance(turn, dict):
        for key in [
            "input",
            "message",
            "query",
            "text",
            "user",
            "content",
            "prompt",
        ]:
            value = turn.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def extract_turns(case: Dict[str, Any]) -> List[str]:
    for key in [
        "turns",
        "messages",
        "conversation",
        "inputs",
        "steps",
        "dialogue",
        "sequence",
    ]:
        value = case.get(key)

        if isinstance(value, list):
            turns = [extract_text_from_turn(v) for v in value]
            turns = [t for t in turns if t]
            if turns:
                return turns

    value = case.get("input") or case.get("message") or case.get("query") or case.get("text")

    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        turns = [extract_text_from_turn(v) for v in value]
        return [t for t in turns if t]

    return []


def to_response_dict(response: Any) -> Dict[str, Any]:
    safe = make_json_safe(response)
    return safe if isinstance(safe, dict) else {"raw_response": safe}


def call_orchestrator(orchestrator: NutritionOrchestrator, text: str) -> Dict[str, Any]:
    for method_name in ["handle_message", "process", "run", "execute"]:
        method = getattr(orchestrator, method_name, None)
        if callable(method):
            return to_response_dict(method(text))

    raise AttributeError("NutritionOrchestrator has no supported execution method.")


def get_nested(obj: Dict[str, Any], *keys, default=None):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def extract_items(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ["items", "calorie_items", "matched_items_details"]:
        value = response.get(key)
        if isinstance(value, list):
            return value

    nested_items = get_nested(response, "calorie_result", "items", default=None)
    if isinstance(nested_items, list):
        return nested_items

    return []


def item_is_matched(item: Dict[str, Any]) -> bool:
    status = str(item.get("status", "")).lower()

    if status in {"ok", "matched", "success", "accepted"}:
        return True

    if item.get("matched_food") or item.get("matched_item") or item.get("food_item"):
        if not item.get("why_rejected"):
            return True

    calories = (
        item.get("calories")
        or item.get("estimated_calories")
        or item.get("total_calories")
    )
    try:
        return float(calories) > 0
    except Exception:
        return False


def extract_meal_state(response: Dict[str, Any]) -> Dict[str, Any]:
    for key in ["meal_state", "meal", "current_meal"]:
        value = response.get(key)
        if isinstance(value, dict):
            return value
    return {}


def extract_summary(response: Dict[str, Any]) -> Dict[str, Any]:
    summary = response.get("summary") or {}
    meal_state = extract_meal_state(response)
    items = extract_items(response)

    total_calories = (
        response.get("total_calories")
        or summary.get("total_calories")
        or get_nested(response, "calorie_result", "total_calories", default=None)
        or 0
    )

    meal_total = (
        response.get("meal_total")
        or summary.get("meal_total")
        or meal_state.get("total_calories")
        or meal_state.get("total")
        or 0
    )

    matched_items = (
        response.get("matched_items")
        or summary.get("matched_items")
        or response.get("matched_count")
        or meal_state.get("matched_items")
    )

    total_items = (
        response.get("total_items")
        or summary.get("total_items")
        or response.get("item_count")
        or meal_state.get("total_items")
    )

    if matched_items is None:
        matched_items = sum(
            1 for item in items
            if isinstance(item, dict) and item_is_matched(item)
        )

    if total_items is None:
        total_items = len(items)

    coverage_raw = response.get("coverage") or summary.get("coverage")
    coverage = parse_coverage(coverage_raw)

    return {
        "mode": response.get("mode") or summary.get("mode"),
        "total_calories": float(total_calories or 0),
        "meal_total": float(meal_total or 0),
        "matched_items": int(matched_items or 0),
        "total_items": int(total_items or 0),
        "coverage": coverage,
        "coverage_raw": coverage_raw,
    }


def close_enough(actual: Any, expected: Any, tolerance: float = 1.0) -> bool:
    try:
        return math.isclose(float(actual), float(expected), abs_tol=tolerance)
    except Exception:
        return False


def evaluate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case.get("case_id")
    category = case.get("category")
    expected = case.get("expected", {})

    orchestrator = NutritionOrchestrator()

    turns = extract_turns(case)
    last_response: Dict[str, Any] = {}

    for text in turns:
        last_response = call_orchestrator(orchestrator, text)

    summary = extract_summary(last_response)
    errors: List[str] = []

    if "mode" in expected:
        actual = summary.get("mode")
        if actual != expected["mode"]:
            errors.append(f"Expected mode={expected['mode']}, got {actual}")

    if "total_calories" in expected:
        actual = summary["total_calories"]
        if not close_enough(actual, expected["total_calories"]):
            errors.append(f"Expected total_calories≈{expected['total_calories']}, got {actual}")

    if "meal_total" in expected:
        actual = summary["meal_total"]
        if not close_enough(actual, expected["meal_total"]):
            errors.append(f"Expected meal_total≈{expected['meal_total']}, got {actual}")

    if "matched_items" in expected:
        actual = summary["matched_items"]
        if actual < int(expected["matched_items"]):
            errors.append(f"Expected matched_items>={expected['matched_items']}, got {actual}")

    if "total_items" in expected:
        actual = summary["total_items"]
        if actual != int(expected["total_items"]):
            errors.append(f"Expected total_items={expected['total_items']}, got {actual}")

    if "coverage" in expected:
        actual = summary["coverage"]
        if actual is not None and not close_enough(actual, expected["coverage"], tolerance=0.05):
            errors.append(f"Expected coverage≈{expected['coverage']}, got {summary['coverage_raw']}")

    return make_json_safe({
        "case_id": case_id,
        "category": category,
        "input": case.get("input") or case.get("turns") or case.get("messages") or case.get("inputs"),
        "turns_used": turns,
        "passed": len(errors) == 0,
        "errors": errors,
        "expected": expected,
        "actual_summary": summary,
        "actual_response": last_response,
    })


def build_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])

    breakdown: Dict[str, Dict[str, Any]] = {}

    for result in results:
        category = result["category"]
        breakdown.setdefault(category, {"total": 0, "passed": 0, "failed": 0})
        breakdown[category]["total"] += 1

        if result["passed"]:
            breakdown[category]["passed"] += 1
        else:
            breakdown[category]["failed"] += 1

    for row in breakdown.values():
        row["pass_rate"] = round(row["passed"] / row["total"] * 100, 2)

    return make_json_safe({
        "dataset_path": str(DATASET_PATH.resolve()),
        "summary": {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": total - passed,
            "pass_rate": round(passed / total * 100, 2) if total else 0,
        },
        "category_breakdown": breakdown,
        "failed_cases": [
            {
                "case_id": r["case_id"],
                "category": r["category"],
                "input": r["input"],
                "turns_used": r["turns_used"],
                "errors": r["errors"],
            }
            for r in results
            if not r["passed"]
        ],
        "detailed_results": results,
    })


def print_report(report: Dict[str, Any]) -> None:
    summary = report["summary"]

    print("Nutrition Assistant Evaluation Report")
    print("=" * 70)
    print(f"Dataset path    : {report['dataset_path']}")
    print(f"Total cases     : {summary['total_cases']}")
    print(f"Passed cases    : {summary['passed_cases']}")
    print(f"Failed cases    : {summary['failed_cases']}")
    print(f"Pass rate       : {summary['pass_rate']:.2f}%")
    print(f"Report written  : {OUTPUT_PATH.resolve()}")
    print("=" * 70)

    print("\nCategory breakdown")
    print("=" * 70)
    print(f"{'Category':<10} {'Total':>8} {'Passed':>9} {'Failed':>9} {'Pass Rate':>12}")
    print("-" * 70)

    for category, row in sorted(report["category_breakdown"].items()):
        print(
            f"{category:<10} "
            f"{row['total']:>8} "
            f"{row['passed']:>9} "
            f"{row['failed']:>9} "
            f"{row['pass_rate']:>11.2f}%"
        )

    print("=" * 70)

    if report["failed_cases"]:
        print("\nFailed cases:")
        for failure in report["failed_cases"]:
            print(f"- {failure['case_id']} [{failure['category']}]:")
            print(f"    turns_used: {failure['turns_used']}")
            for error in failure["errors"]:
                print(f"    * {error}")


def main() -> None:
    cases = json.loads(DATASET_PATH.read_text())
    results = [evaluate_case(case) for case in cases]
    report = build_report(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print_report(report)


if __name__ == "__main__":
    main()