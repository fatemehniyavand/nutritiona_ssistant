import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


DATASET_PATH = Path("eval/datasets/eval_cases_adversarial.json")
OUTPUT_PATH = Path("eval/outputs/eval_report_adversarial.json")


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
        return to_serializable(
            {k: v for k, v in vars(value).items() if not callable(v) and not k.startswith("_")}
        )
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


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"{DATASET_PATH} not found. Run generate_adversarial_eval_dataset.py first.")

    with DATASET_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    orchestrator = NutritionOrchestrator()
    passed = 0
    failed = 0
    score_sum = 0.0
    failed_cases = []

    print("=" * 70)
    print("Running ADVERSARIAL evaluation")
    print("=" * 70)
    print(f"Using dataset: {DATASET_PATH.resolve()}")
    print("=" * 70)

    for case in cases:
        response = invoke(orchestrator, case["input"])
        expected = case["expected"]

        mode = get_mode(response)
        matched_items = get_matched_items(response)
        total_items = get_total_items(response)
        total_calories = get_total_calories(response)
        final_message = lower_text(get_final_message(response))

        ok = True
        errors = []
        score = 100.0

        expected_mode = lower_text(expected.get("mode"))
        if expected_mode and mode != expected_mode:
            ok = False
            errors.append(f"Expected mode={expected_mode}, got {mode}")
            score -= 15

        exp_matched_min = safe_int(expected.get("matched_items_min"))
        if exp_matched_min is not None and matched_items < exp_matched_min:
            ok = False
            errors.append(f"Expected matched_items>={exp_matched_min}, got {matched_items}")
            score -= 20

        exp_total_items_min = safe_int(expected.get("total_items_min"))
        if exp_total_items_min is not None and total_items < exp_total_items_min:
            ok = False
            errors.append(f"Expected total_items>={exp_total_items_min}, got {total_items}")
            score -= 20

        exp_total_cal = safe_float(expected.get("total_calories"))
        if exp_total_cal is not None and total_calories is not None:
            if not approx_equal(total_calories, exp_total_cal, 15.0):
                ok = False
                errors.append(f"Expected total_calories≈{exp_total_cal}, got {total_calories}")
                score -= 25

        if expected.get("message_non_empty") and not final_message:
            ok = False
            errors.append("Expected non-empty final_message")
            score -= 20

        score = max(0.0, round(score, 2))
        score_sum += score

        if ok:
            passed += 1
        else:
            failed += 1
            failed_cases.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "input": case["input"],
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
        "failed_cases": failed_cases,
    }

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

    if failed_cases:
        print()
        print("Failed cases:")
        for case in failed_cases[:100]:
            print(f"- {case['case_id']} [{case['category']}]:")
            for err in case["errors"]:
                print(f"    * {err}")


if __name__ == "__main__":
    main()