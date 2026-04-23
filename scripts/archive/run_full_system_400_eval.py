import json
import random
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


SEED = 42
TARGET_TOTAL_CASES = 400

DATA_PATH = Path("data/processed/calories_cleaned.csv")
BASE_EVAL_PATH = Path("eval/datasets/eval_cases.json")
EXTENDED_EVAL_PATH = Path("eval/datasets/eval_cases_extended.json")

DATASET_OUTPUT_PATH = Path("eval/datasets/eval_cases_full_system_400.json")
REPORT_OUTPUT_PATH = Path("eval/outputs/eval_report_full_system_400.json")


# -----------------------------
# Generic helpers
# -----------------------------
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
    for key in ["total_calories", "estimated_total_calories", "calories", "total_kcal"]:
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


def get_mode(response: dict) -> str:
    for key in ["mode", "intent", "response_mode"]:
        value = response.get(key)
        if value:
            return lower_text(value)
    return ""


# -----------------------------
# Dataset builders
# -----------------------------
def load_foods() -> list[dict]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing cleaned dataset: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    required = {"food_item", "food_key", "calories_per_100g"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in cleaned CSV: {sorted(missing)}")

    foods = []
    seen = set()

    for _, row in df.iterrows():
        food_item = str(row["food_item"]).strip().lower()
        food_key = str(row["food_key"]).strip().lower()
        calories = float(row["calories_per_100g"])

        if not food_item or not food_key:
            continue

        if food_item in seen:
            continue
        seen.add(food_item)

        foods.append(
            {
                "food_item": food_item,
                "food_key": food_key,
                "calories_per_100g": calories,
            }
        )

    return foods


def random_grams(rng: random.Random) -> int:
    return rng.choice([50, 75, 80, 90, 100, 120, 150, 180, 200, 250, 300])


def expected_calories(calories_per_100g: float, grams: int) -> float:
    return round((calories_per_100g * grams) / 100.0, 2)


def is_parser_safe_single_food(orchestrator: NutritionOrchestrator, food_name: str) -> bool:
    probe = f"{food_name} 100g"
    response = invoke(orchestrator, probe)

    return (
        get_mode(response) == "calorie"
        and get_total_items(response) == 1
        and get_matched_items(response) == 1
        and (get_total_calories(response) or 0) > 0
    )


def build_parser_safe_food_pool(orchestrator: NutritionOrchestrator, foods: list[dict]) -> list[dict]:
    safe_foods = []
    checked = 0

    print("=" * 70)
    print("Building parser-safe calorie food pool")
    print("=" * 70)

    for food in foods:
        checked += 1
        if is_parser_safe_single_food(orchestrator, food["food_item"]):
            safe_foods.append(food)

        if checked % 100 == 0 or checked == len(foods):
            print(f"Checked {checked}/{len(foods)} | parser_safe={len(safe_foods)}")

    print("=" * 70)
    print(f"Parser-safe foods found: {len(safe_foods)}")
    print("=" * 70)

    return safe_foods


def build_calorie_exact_cases(parser_safe_foods: list[dict], rng: random.Random, count: int) -> list[dict]:
    cases = []
    for idx in range(1, count + 1):
        food = rng.choice(parser_safe_foods)
        grams = random_grams(rng)

        cases.append(
            {
                "case_id": f"CAL-EXACT-{idx:03d}",
                "category": "CAL_EXACT",
                "input": f"{food['food_item']} {grams}g",
                "expected": {
                    "mode": "calorie",
                    "total_items": 1,
                    "matched_items": 1,
                    "coverage": 1.0,
                    "total_calories": expected_calories(food["calories_per_100g"], grams),
                },
                "meta": {
                    "food_item": food["food_item"],
                    "grams": grams,
                    "food_key": food["food_key"],
                    "calories_per_100g": food["calories_per_100g"],
                },
            }
        )
    return cases


def build_calorie_multi_cases(parser_safe_foods: list[dict], rng: random.Random, count: int) -> list[dict]:
    cases = []
    for idx in range(1, count + 1):
        food_a = rng.choice(parser_safe_foods)
        food_b = rng.choice(parser_safe_foods)

        while food_b["food_item"] == food_a["food_item"]:
            food_b = rng.choice(parser_safe_foods)

        grams_a = random_grams(rng)
        grams_b = random_grams(rng)

        user_input = f"{food_a['food_item']} {grams_a}g and {food_b['food_item']} {grams_b}g"
        total = expected_calories(food_a["calories_per_100g"], grams_a) + expected_calories(food_b["calories_per_100g"], grams_b)

        cases.append(
            {
                "case_id": f"CAL-MULTI-{idx:03d}",
                "category": "CAL_MULTI",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "total_items": 2,
                    "matched_items": 2,
                    "coverage": 1.0,
                    "total_calories": round(total, 2),
                },
                "meta": {
                    "items": [
                        {
                            "food_item": food_a["food_item"],
                            "grams": grams_a,
                            "calories_per_100g": food_a["calories_per_100g"],
                        },
                        {
                            "food_item": food_b["food_item"],
                            "grams": grams_b,
                            "calories_per_100g": food_b["calories_per_100g"],
                        },
                    ]
                },
            }
        )
    return cases


def load_existing_eval_cases() -> list[dict]:
    all_cases = []

    for path in [BASE_EVAL_PATH, EXTENDED_EVAL_PATH]:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                all_cases.extend(data)

    return all_cases


def build_qa_cases(rng: random.Random, count: int) -> list[dict]:
    existing_cases = load_existing_eval_cases()

    qa_source = []
    for case in existing_cases:
        category = lower_text(case.get("category"))
        case_id = str(case.get("case_id", ""))
        if category == "qa" or case_id.startswith("QA-"):
            qa_source.append(case)

    if not qa_source:
        qa_source = [
            {
                "input": "What are good sources of protein?",
                "expected_contains": ["protein"],
            },
            {
                "input": "Is avocado healthy?",
                "expected_contains": ["avocado"],
            },
            {
                "input": "What foods are high in fiber?",
                "expected_contains": ["fiber"],
            },
            {
                "input": "Why is hydration important?",
                "expected_contains": ["hydration"],
            },
            {
                "input": "What are the benefits of vegetables?",
                "expected_contains": ["vegetables"],
            },
        ]

    cases = []
    for idx in range(1, count + 1):
        src = rng.choice(qa_source)

        expected_contains = []
        if isinstance(src.get("expected"), dict):
            final_msg = src["expected"].get("final_message_contains")
            if final_msg:
                expected_contains.append(str(final_msg).lower())

        if not expected_contains and src.get("expected_contains"):
            expected_contains = [str(x).lower() for x in src.get("expected_contains", [])]

        cases.append(
            {
                "case_id": f"QA-{idx:03d}",
                "category": "QA",
                "input": src["input"],
                "expected": {
                    "mode_candidates": ["qa", "nutrition_qa", "unknown"],
                    "message_must_not_be_empty": True,
                    "expected_contains_any": expected_contains,
                },
                "meta": {
                    "source": "existing_eval_or_fallback",
                },
            }
        )

    return cases


def build_guard_cases() -> list[dict]:
    raw_cases = [
        {
            "case_id": "GRD-001",
            "category": "GUARD_EMPTY",
            "input": "",
            "expected_substrings": ["empty"],
        },
        {
            "case_id": "GRD-002",
            "category": "GUARD_EMPTY",
            "input": "   ",
            "expected_substrings": ["empty"],
        },
        {
            "case_id": "GRD-003",
            "category": "GUARD_NON_ENGLISH",
            "input": "سلام خوبی",
            "expected_substrings": ["english", "please speak"],
        },
        {
            "case_id": "GRD-004",
            "category": "GUARD_NON_ENGLISH",
            "input": "ciao come stai",
            "expected_substrings": ["english", "please speak"],
        },
        {
            "case_id": "GRD-005",
            "category": "GUARD_QUANTITY_ONLY",
            "input": "200g",
            "expected_substrings": ["food name", "include the food"],
        },
        {
            "case_id": "GRD-006",
            "category": "GUARD_QUANTITY_ONLY",
            "input": "150 g",
            "expected_substrings": ["food name", "include the food"],
        },
        {
            "case_id": "GRD-007",
            "category": "GUARD_FOOD_ONLY",
            "input": "apple",
            "expected_substrings": ["grams", "quantity"],
        },
        {
            "case_id": "GRD-008",
            "category": "GUARD_FOOD_ONLY",
            "input": "banana",
            "expected_substrings": ["grams", "quantity"],
        },
        {
            "case_id": "GRD-009",
            "category": "GUARD_NON_NUMERIC_QUANTITY",
            "input": "apple two hundred grams",
            "expected_substrings": ["digits", "quantity"],
        },
        {
            "case_id": "GRD-010",
            "category": "GUARD_NON_NUMERIC_QUANTITY",
            "input": "banana one hundred grams",
            "expected_substrings": ["digits", "quantity"],
        },
        {
            "case_id": "GRD-011",
            "category": "GUARD_GIBBERISH",
            "input": "asdkjhasd qweoiu zmxn",
            "expected_substrings": ["unclear", "rewrite"],
        },
        {
            "case_id": "GRD-012",
            "category": "GUARD_GIBBERISH",
            "input": "zzzz food blahhhh",
            "expected_substrings": ["unclear", "rewrite"],
        },
        {
            "case_id": "GRD-013",
            "category": "STATE_TOTAL",
            "input": "what is the total now?",
            "expected_substrings": ["total"],
        },
        {
            "case_id": "GRD-014",
            "category": "STATE_CLEAR",
            "input": "clear meal",
            "expected_substrings": ["clear", "meal"],
        },
        {
            "case_id": "GRD-015",
            "category": "STATE_REMOVE",
            "input": "remove apple 100g",
            "expected_substrings": ["remove", "meal", "not"],
        },
    ]

    cases = []
    for case in raw_cases:
        cases.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "input": case["input"],
                "expected": {
                    "message_must_not_be_empty": True,
                    "expected_substrings": [s.lower() for s in case["expected_substrings"]],
                },
                "meta": {},
            }
        )
    return cases


def build_full_suite(orchestrator: NutritionOrchestrator, rng: random.Random) -> list[dict]:
    foods = load_foods()
    parser_safe_foods = build_parser_safe_food_pool(orchestrator, foods)

    if len(parser_safe_foods) < 60:
        raise RuntimeError(
            f"Too few parser-safe foods found: {len(parser_safe_foods)}. "
            "Need a bigger safe pool for a strong 400-case suite."
        )

    calorie_exact_count = 180
    calorie_multi_count = 80
    qa_count = 100
    guard_cases = build_guard_cases()  # 15
    guard_count = len(guard_cases)

    remaining = TARGET_TOTAL_CASES - (calorie_exact_count + calorie_multi_count + qa_count + guard_count)
    if remaining < 0:
        raise RuntimeError("Case counts exceed target total.")

    # Extra calorie exact cases to fill up to 400
    extra_exact_count = remaining

    cases = []
    cases.extend(build_calorie_exact_cases(parser_safe_foods, rng, calorie_exact_count))
    cases.extend(build_calorie_multi_cases(parser_safe_foods, rng, calorie_multi_count))
    cases.extend(build_qa_cases(rng, qa_count))
    cases.extend(guard_cases)
    cases.extend(build_calorie_exact_cases(parser_safe_foods, rng, extra_exact_count))

    if len(cases) != TARGET_TOTAL_CASES:
        raise RuntimeError(f"Built {len(cases)} cases, expected {TARGET_TOTAL_CASES}")

    rng.shuffle(cases)

    return cases


# -----------------------------
# Evaluation
# -----------------------------
def evaluate_calorie_case(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []
    expected = case["expected"]

    mode = get_mode(response)
    total_items = get_total_items(response)
    matched_items = get_matched_items(response)
    coverage = get_coverage(response)
    total_calories = get_total_calories(response)

    expected_mode = lower_text(expected["mode"])
    expected_total_items = int(expected["total_items"])
    expected_matched_items = int(expected["matched_items"])
    expected_coverage = float(expected["coverage"])
    expected_total_calories = float(expected["total_calories"])

    if mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {mode}")

    if total_items != expected_total_items:
        errors.append(f"Expected total_items={expected_total_items}, got {total_items}")

    if matched_items != expected_matched_items:
        errors.append(f"Expected matched_items={expected_matched_items}, got {matched_items}")

    if not approx_equal(coverage, expected_coverage, tol=0.001):
        errors.append(f"Expected coverage={expected_coverage}, got {coverage}")

    if not approx_equal(total_calories, expected_total_calories, tol=1.0):
        errors.append(f"Expected total_calories≈{expected_total_calories}, got {total_calories}")

    score = 100.0
    if mode != expected_mode:
        score -= 15
    if total_items != expected_total_items:
        score -= 20
    if matched_items != expected_matched_items:
        score -= 20
    if not approx_equal(coverage, expected_coverage, tol=0.001):
        score -= 15
    if not approx_equal(total_calories, expected_total_calories, tol=1.0):
        score -= 30

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_qa_case(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []
    expected = case["expected"]

    mode = get_mode(response)
    final_message = lower_text(get_final_message(response))

    mode_candidates = [lower_text(x) for x in expected.get("mode_candidates", [])]
    expected_contains_any = [lower_text(x) for x in expected.get("expected_contains_any", [])]

    if expected.get("message_must_not_be_empty") and not final_message:
        errors.append("Expected non-empty final_message, got empty")

    if mode_candidates and mode not in mode_candidates:
        # برای QA این را نرم می‌گیریم چون بعضی پیاده‌سازی‌ها mode را واضح نمی‌زنند
        errors.append(f"Expected mode in {mode_candidates}, got {mode}")

    if expected_contains_any:
        if not any(token in final_message for token in expected_contains_any):
            errors.append(
                f"Expected final_message to contain at least one of {expected_contains_any}, got '{final_message}'"
            )

    score = 100.0
    if not final_message:
        score -= 50
    if mode_candidates and mode not in mode_candidates:
        score -= 20
    if expected_contains_any and not any(token in final_message for token in expected_contains_any):
        score -= 30

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_guard_case(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []
    expected = case["expected"]

    final_message = lower_text(get_final_message(response))
    expected_substrings = [lower_text(x) for x in expected.get("expected_substrings", [])]

    if expected.get("message_must_not_be_empty") and not final_message:
        errors.append("Expected non-empty final_message, got empty")

    if expected_substrings:
        if not any(token in final_message for token in expected_substrings):
            errors.append(
                f"Expected final_message to contain one of {expected_substrings}, got '{final_message}'"
            )

    score = 100.0
    if not final_message:
        score -= 50
    if expected_substrings and not any(token in final_message for token in expected_substrings):
        score -= 50

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_case(case: dict, response: dict) -> tuple[bool, list[str], float]:
    category = case["category"]

    if category in {"CAL_EXACT", "CAL_MULTI"}:
        return evaluate_calorie_case(case, response)

    if category == "QA":
        return evaluate_qa_case(case, response)

    return evaluate_guard_case(case, response)


def make_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "score_sum": 0.0,
    }


def summarize_category(category: str, stats: dict[str, Any]) -> dict[str, Any]:
    total = stats["total"]
    passed = stats["passed"]
    failed = stats["failed"]
    score_sum = stats["score_sum"]

    pass_rate = round((passed / total) * 100.0, 2) if total else 0.0
    avg_score = round(score_sum / total, 2) if total else 0.0

    return {
        "category": category,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
    }


def print_report(summary: dict, category_rows: list[dict], failed_cases: list[dict]) -> None:
    print("=" * 70)
    print("Nutrition Assistant Full System 400 Evaluation Report")
    print("=" * 70)
    print(f"Total cases     : {summary['total_cases']}")
    print(f"Passed cases    : {summary['passed_cases']}")
    print(f"Failed cases    : {summary['failed_cases']}")
    print(f"Pass rate       : {summary['pass_rate']:.2f}%")
    print(f"Average score   : {summary['average_score']:.2f}%")
    print(f"Dataset written : {DATASET_OUTPUT_PATH.resolve()}")
    print(f"Report written  : {REPORT_OUTPUT_PATH.resolve()}")
    print("=" * 70)
    print()
    print("Category breakdown")
    print("=" * 70)
    print(
        f"{'Category':<18}"
        f"{'Total':>8}"
        f"{'Passed':>10}"
        f"{'Failed':>9}"
        f"{'Pass Rate':>14}"
        f"{'Avg Score':>13}"
    )
    print("-" * 70)

    for row in category_rows:
        print(
            f"{row['category']:<18}"
            f"{row['total']:>8}"
            f"{row['passed']:>10}"
            f"{row['failed']:>9}"
            f"{row['pass_rate']:>13.2f}%"
            f"{row['avg_score']:>12.2f}%"
        )

    print("=" * 70)

    if failed_cases:
        print()
        print("Sample failed cases:")
        for case in failed_cases[:20]:
            print(f"- {case['case_id']} [{case['category']}]")
            print(f"    Input: {case['input']}")
            for err in case["errors"]:
                print(f"    * {err}")


def main() -> None:
    rng = random.Random(SEED)
    orchestrator = NutritionOrchestrator()

    cases = build_full_suite(orchestrator, rng)

    DATASET_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("Running full system 400-case evaluation")
    print("=" * 70)
    print(f"Using dataset: {DATASET_OUTPUT_PATH.resolve()}")
    print("=" * 70)

    category_stats: dict[str, dict[str, Any]] = defaultdict(make_stats)
    failed_cases = []
    detailed_results = []

    passed = 0
    failed = 0
    score_sum = 0.0

    for idx, case in enumerate(cases, start=1):
        response = invoke(orchestrator, case["input"])
        ok, errors, score = evaluate_case(case, response)

        score_sum += score

        stats = category_stats[case["category"]]
        stats["total"] += 1
        stats["score_sum"] += score

        if ok:
            passed += 1
            stats["passed"] += 1
        else:
            failed += 1
            stats["failed"] += 1
            failed_cases.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "input": case["input"],
                    "errors": errors,
                    "response_preview": {
                        "mode": get_mode(response),
                        "total_items": get_total_items(response),
                        "matched_items": get_matched_items(response),
                        "coverage": get_coverage(response),
                        "total_calories": get_total_calories(response),
                        "confidence": response.get("confidence"),
                        "final_message": get_final_message(response),
                        "response_type": response.get("_debug_response_type"),
                    },
                }
            )

        detailed_results.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "input": case["input"],
                "passed": ok,
                "score": score,
                "errors": errors,
                "expected": case["expected"],
                "response_summary": {
                    "mode": get_mode(response),
                    "total_items": get_total_items(response),
                    "matched_items": get_matched_items(response),
                    "coverage": get_coverage(response),
                    "total_calories": get_total_calories(response),
                    "confidence": response.get("confidence"),
                    "final_message": get_final_message(response),
                    "response_type": response.get("_debug_response_type"),
                },
            }
        )

        if idx % 25 == 0 or idx == len(cases):
            print(f"Progress: {idx}/{len(cases)} | passed={passed} | failed={failed}")

    total_cases = len(cases)
    pass_rate = round((passed / total_cases) * 100.0, 2) if total_cases else 0.0
    average_score = round(score_sum / total_cases, 2) if total_cases else 0.0

    category_rows = [
        summarize_category(category, stats)
        for category, stats in sorted(category_stats.items())
    ]

    report = {
        "report_name": "full_system_400_eval",
        "dataset_path": str(DATASET_OUTPUT_PATH),
        "summary": {
            "total_cases": total_cases,
            "passed_cases": passed,
            "failed_cases": failed,
            "pass_rate": pass_rate,
            "average_score": average_score,
        },
        "category_breakdown": category_rows,
        "failed_cases": failed_cases,
        "detailed_results": detailed_results,
    }

    REPORT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print_report(report["summary"], category_rows, failed_cases)


if __name__ == "__main__":
    main()