import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


def response_to_dict(response) -> dict:
    if isinstance(response, dict):
        return response

    try:
        return response.model_dump()
    except Exception:
        pass

    try:
        return response.dict()
    except Exception:
        pass

    data = {}

    for key in dir(response):
        if key.startswith("_"):
            continue

        value = getattr(response, key, None)

        if callable(value):
            continue

        data[key] = value

    return data


def response_to_text(response) -> str:
    return json.dumps(response_to_dict(response), ensure_ascii=False, default=str)


def get_response_value(response, key, default=None):
    data = response_to_dict(response)
    return data.get(key, default)


def get_mode(response) -> str:
    return str(get_response_value(response, "mode", "") or "").lower()


def get_items(response) -> list:
    items = get_response_value(response, "items", [])

    if items is None:
        return []

    if callable(items):
        return []

    if not isinstance(items, list):
        return []

    return items


def item_value(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)

    value = getattr(item, key, default)

    if callable(value):
        return default

    return value


def check_case_output(case, response_text, response):
    text = response_text.lower()
    errors = []

    expected_mode = str(case.get("expected_mode", "") or "").lower()
    actual_mode = get_mode(response)

    if expected_mode:
        if expected_mode == "calorie":
            if actual_mode != "calorie":
                errors.append(f"mode expected calorie, got {actual_mode}")
        elif expected_mode == "nutrition_qa":
            if actual_mode != "nutrition_qa":
                errors.append(f"mode expected nutrition_qa, got {actual_mode}")
        elif expected_mode == "guard":
            if actual_mode not in {"guard", "nutrition_qa", "out_of_scope"}:
                errors.append(f"mode expected guard-like, got {actual_mode}")
        elif expected_mode == "daily_tracking":
            if actual_mode != "daily_tracking":
                errors.append(f"mode expected daily_tracking, got {actual_mode}")

    for term in case.get("must_contain", []) or []:
        if str(term).lower() not in text:
            errors.append(f"missing required term: {term}")

    any_terms = case.get("must_contain_any", []) or []
    if any_terms:
        if not any(str(term).lower() in text for term in any_terms):
            errors.append(f"none of must_contain_any found: {any_terms}")

    for term in case.get("must_not_contain", []) or []:
        if term and str(term).lower() in text:
            errors.append(f"forbidden term found: {term}")

    expected_total = case.get("expected_total_calories", None)
    if expected_total is not None:
        actual_total = get_response_value(response, "total_calories", None)

        if actual_total is None:
            errors.append("expected total_calories but response has none")
        else:
            if abs(float(actual_total) - float(expected_total)) > 1.0:
                errors.append(f"total mismatch: expected {expected_total}, got {actual_total}")

    expected_foods = case.get("expected_matched_foods", None)
    if expected_foods is not None:
        items = get_items(response)
        matched = []

        for item in items:
            status = str(item_value(item, "status", "") or "").lower()
            matched_food = item_value(item, "matched_food", None)

            if matched_food and status in {"matched", "ok", "success"}:
                matched.append(str(matched_food).lower())

        for food in expected_foods:
            if not any(str(food).lower() in m for m in matched):
                errors.append(f"expected matched food missing: {food}")

        if expected_foods == [] and matched:
            errors.append(f"expected no matched foods, got {matched}")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="eval/datasets/eval_FINAL_BOSS_500.json")
    parser.add_argument("--output", default="eval/outputs/boss_eval_report.json")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    results = []
    passed = 0
    failed = 0

    for case in cases:
        orch = NutritionOrchestrator()
        case_errors = []
        step_results = []

        if "steps" in case:
            for idx, step in enumerate(case["steps"], start=1):
                response = orch.run(step.get("input", ""))
                text = response_to_text(response)
                errors = check_case_output(step, text, response)

                step_results.append(
                    {
                        "step": idx,
                        "input": step.get("input", ""),
                        "passed": not errors,
                        "errors": errors,
                        "response": response_to_dict(response),
                    }
                )

                case_errors.extend([f"step {idx}: {e}" for e in errors])
        else:
            response = orch.run(case.get("input", ""))
            text = response_to_text(response)
            case_errors = check_case_output(case, text, response)

            step_results.append(
                {
                    "step": 1,
                    "input": case.get("input", ""),
                    "passed": not case_errors,
                    "errors": case_errors,
                    "response": response_to_dict(response),
                }
            )

        ok = not case_errors

        if ok:
            passed += 1
        else:
            failed += 1

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "passed": ok,
                "errors": case_errors,
                "steps": step_results,
            }
        )

    category_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    for result in results:
        category = result["category"]
        category_stats[category]["total"] += 1

        if result["passed"]:
            category_stats[category]["passed"] += 1
        else:
            category_stats[category]["failed"] += 1

    report = {
        "dataset": str(dataset_path),
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "pass_rate": round((passed / len(cases)) * 100, 2) if cases else 0,
        "category_breakdown": dict(category_stats),
        "results": results,
    }

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("=" * 70)
    print("BOSS EVALUATION REPORT")
    print("=" * 70)
    print(f"Dataset   : {dataset_path}")
    print(f"Total     : {len(cases)}")
    print(f"Passed    : {passed}")
    print(f"Failed    : {failed}")
    print(f"Pass rate : {report['pass_rate']}%")
    print(f"Report    : {output_path}")
    print("=" * 70)

    if failed:
        print("\nFAILED CASES:")
        for result in results:
            if not result["passed"]:
                print(f"- {result['id']} [{result['category']}]")
                for error in result["errors"][:5]:
                    print(f"  - {error}")


if __name__ == "__main__":
    main()
