import json
import random
import re
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator


SEED = 42
TARGET_TOTAL_CASES = 400

CALORIE_DATA_PATH = Path("data/processed/calories_cleaned.csv")
QA_TEXT_PATH = Path("data/processed/questions_output.txt")

DATASET_OUTPUT_PATH = Path("eval/datasets/eval_cases_dataset_aligned_400.json")
REPORT_OUTPUT_PATH = Path("eval/outputs/eval_report_dataset_aligned_400.json")


# --------------------------------
# Generic helpers
# --------------------------------
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


# --------------------------------
# Semantic guard helpers
# --------------------------------
def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)


def _looks_like_empty_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "type a food query",
            "type a nutrition question",
            "example:",
            "apple 200g",
            "is avocado healthy",
        ],
    )


def _looks_like_food_only_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "apple 200g",
            "banana 200g",
            "200g",
            "grams",
            "quantity",
            "try:",
            "example:",
        ],
    )


def _looks_like_gibberish_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "clear english food name",
            "please type",
            "example:",
            "apple 200g",
            "rewrite",
            "unclear",
        ],
    )


def _looks_like_non_english_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "in english",
            "english",
            "example:",
            "apple 200g",
            "is avocado healthy",
            "please type",
        ],
    )


def _looks_like_quantity_only_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "food",
            "include",
            "food name",
            "apple 200g",
            "example:",
        ],
    )


def _looks_like_non_numeric_quantity_guard(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "digits",
            "quantity",
            "apple 200g",
            "example:",
        ],
    )


def _looks_like_state_total(msg: str) -> bool:
    return _contains_any(
        msg,
        [
            "total",
            "meal is empty",
            "current meal",
            "empty",
        ],
    )


def semantic_guard_match(category: str, final_message: str) -> bool:
    msg = lower_text(final_message)

    if not msg:
        return False

    mapping = {
        "GUARD_EMPTY": _looks_like_empty_guard,
        "GUARD_FOOD_ONLY": _looks_like_food_only_guard,
        "GUARD_GIBBERISH": _looks_like_gibberish_guard,
        "GUARD_NON_ENGLISH": _looks_like_non_english_guard,
        "GUARD_QUANTITY_ONLY": _looks_like_quantity_only_guard,
        "GUARD_NON_NUMERIC_QUANTITY": _looks_like_non_numeric_quantity_guard,
        "STATE_TOTAL": _looks_like_state_total,
    }

    fn = mapping.get(category)
    if fn is None:
        return False

    return fn(msg)


# --------------------------------
# Dataset loading
# --------------------------------
def load_calorie_foods() -> list[dict]:
    if not CALORIE_DATA_PATH.exists():
        raise FileNotFoundError(f"Missing calorie dataset: {CALORIE_DATA_PATH}")

    df = pd.read_csv(CALORIE_DATA_PATH)
    required = {"food_item", "food_key", "calories_per_100g"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in calorie dataset: {sorted(missing)}")

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


def load_qa_questions() -> list[str]:
    questions = []

    if QA_TEXT_PATH.exists():
        text = QA_TEXT_PATH.read_text(encoding="utf-8", errors="ignore")
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]

        for block in blocks:
            first_line = block.splitlines()[0].strip()
            if first_line:
                questions.append(first_line)

    if not questions:
        questions = [
            "What are good sources of protein?",
            "Is avocado healthy?",
            "What foods are high in fiber?",
            "Why is hydration important?",
            "What are healthy breakfast ideas?",
        ]

    seen = set()
    unique = []
    for q in questions:
        qn = lower_text(q)
        if qn and qn not in seen:
            seen.add(qn)
            unique.append(q)

    return unique


# --------------------------------
# Case builders
# --------------------------------
def random_grams(rng: random.Random) -> int:
    return rng.choice([50, 75, 80, 90, 100, 120, 150, 180, 200, 250, 300])


def calc_expected_kcal(cal_per_100g: float, grams: int) -> float:
    return round((cal_per_100g * grams) / 100.0, 2)


def calorie_variants(food_name: str, grams: int) -> list[str]:
    return [
        f"{food_name} {grams}g",
        f"{food_name}{grams}g",
        f"add {food_name} {grams}g",
        f"{food_name} {grams} g",
    ]


def build_calorie_single_cases(foods: list[dict], rng: random.Random, count: int) -> list[dict]:
    cases = []
    for idx in range(1, count + 1):
        food = rng.choice(foods)
        grams = random_grams(rng)
        user_input = rng.choice(calorie_variants(food["food_item"], grams))

        cases.append(
            {
                "case_id": f"CAL-SINGLE-{idx:03d}",
                "category": "CAL_SINGLE",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "expected_food_item": food["food_item"],
                    "expected_total_calories": calc_expected_kcal(food["calories_per_100g"], grams),
                    "expected_grams": grams,
                },
                "meta": {
                    "food_item": food["food_item"],
                    "food_key": food["food_key"],
                    "grams": grams,
                    "calories_per_100g": food["calories_per_100g"],
                },
            }
        )
    return cases


def build_calorie_multi_cases(foods: list[dict], rng: random.Random, count: int) -> list[dict]:
    cases = []
    for idx in range(1, count + 1):
        food_a = rng.choice(foods)
        food_b = rng.choice(foods)
        while food_b["food_item"] == food_a["food_item"]:
            food_b = rng.choice(foods)

        grams_a = random_grams(rng)
        grams_b = random_grams(rng)

        formats = [
            f"{food_a['food_item']} {grams_a}g and {food_b['food_item']} {grams_b}g",
            f"add {food_a['food_item']} {grams_a}g and {food_b['food_item']} {grams_b}g",
            f"{food_a['food_item']}{grams_a}g and {food_b['food_item']}{grams_b}g",
        ]
        user_input = rng.choice(formats)

        total = calc_expected_kcal(food_a["calories_per_100g"], grams_a) + calc_expected_kcal(
            food_b["calories_per_100g"], grams_b
        )

        cases.append(
            {
                "case_id": f"CAL-MULTI-{idx:03d}",
                "category": "CAL_MULTI",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "expected_total_calories": round(total, 2),
                    "expected_item_count_min": 1,
                    "expected_item_count_max": 2,
                },
                "meta": {
                    "items": [
                        {"food_item": food_a["food_item"], "grams": grams_a},
                        {"food_item": food_b["food_item"], "grams": grams_b},
                    ]
                },
            }
        )
    return cases


def build_qa_cases(questions: list[str], rng: random.Random, count: int) -> list[dict]:
    cases = []
    for idx in range(1, count + 1):
        q = rng.choice(questions)
        cases.append(
            {
                "case_id": f"QA-{idx:03d}",
                "category": "QA",
                "input": q,
                "expected": {
                    "message_must_not_be_empty": True,
                },
                "meta": {
                    "question": q,
                },
            }
        )
    return cases


def build_guard_cases() -> list[dict]:
    raw = [
        ("GRD-001", "GUARD_EMPTY", ""),
        ("GRD-002", "GUARD_EMPTY", "   "),
        ("GRD-003", "GUARD_NON_ENGLISH", "سلام خوبی"),
        ("GRD-004", "GUARD_NON_ENGLISH", "ciao come stai"),
        ("GRD-005", "GUARD_QUANTITY_ONLY", "200g"),
        ("GRD-006", "GUARD_QUANTITY_ONLY", "150 g"),
        ("GRD-007", "GUARD_FOOD_ONLY", "apple"),
        ("GRD-008", "GUARD_FOOD_ONLY", "banana"),
        ("GRD-009", "GUARD_NON_NUMERIC_QUANTITY", "apple two hundred grams"),
        ("GRD-010", "GUARD_NON_NUMERIC_QUANTITY", "banana one hundred grams"),
        ("GRD-011", "GUARD_GIBBERISH", "asdkjhasd qweoiu zmxn"),
        ("GRD-012", "GUARD_GIBBERISH", "zzzz food blahhhh"),
        ("GRD-013", "STATE_TOTAL", "what is the total now?"),
        ("GRD-014", "STATE_CLEAR", "clear meal"),
        ("GRD-015", "STATE_REMOVE", "remove apple 100g"),
    ]

    cases = []
    for case_id, category, user_input in raw:
        cases.append(
            {
                "case_id": case_id,
                "category": category,
                "input": user_input,
                "expected": {
                    "message_must_not_be_empty": True,
                },
                "meta": {},
            }
        )
    return cases


def build_suite(rng: random.Random) -> list[dict]:
    foods = load_calorie_foods()
    questions = load_qa_questions()

    calorie_single_count = 180
    calorie_multi_count = 120
    qa_count = 85
    guard_cases = build_guard_cases()

    cases = []
    cases.extend(build_calorie_single_cases(foods, rng, calorie_single_count))
    cases.extend(build_calorie_multi_cases(foods, rng, calorie_multi_count))
    cases.extend(build_qa_cases(questions, rng, qa_count))
    cases.extend(guard_cases)

    if len(cases) != TARGET_TOTAL_CASES:
        raise RuntimeError(f"Built {len(cases)} cases, expected {TARGET_TOTAL_CASES}")

    rng.shuffle(cases)
    return cases


# --------------------------------
# Evaluation logic
# --------------------------------
def evaluate_cal_single(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []

    mode = get_mode(response)
    total_calories = get_total_calories(response)
    final_message = lower_text(get_final_message(response))

    expected_mode = lower_text(case["expected"]["mode"])
    expected_total = float(case["expected"]["expected_total_calories"])

    if mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {mode}")

    if total_calories is None:
        errors.append("Expected total_calories, got None")
    elif not approx_equal(total_calories, expected_total, tol=2.0):
        errors.append(f"Expected total_calories≈{expected_total}, got {total_calories}")

    if not final_message:
        errors.append("Expected non-empty final_message")

    score = 100.0
    if mode != expected_mode:
        score -= 20
    if total_calories is None:
        score -= 50
    elif not approx_equal(total_calories, expected_total, tol=2.0):
        score -= 30
    if not final_message:
        score -= 10

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_cal_multi(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []

    mode = get_mode(response)
    total_items = get_total_items(response)
    total_calories = get_total_calories(response)
    final_message = lower_text(get_final_message(response))

    expected_mode = lower_text(case["expected"]["mode"])
    expected_total = float(case["expected"]["expected_total_calories"])
    min_items = int(case["expected"]["expected_item_count_min"])
    max_items = int(case["expected"]["expected_item_count_max"])

    if mode != expected_mode:
        errors.append(f"Expected mode={expected_mode}, got {mode}")

    if not (min_items <= total_items <= max_items):
        errors.append(f"Expected total_items in [{min_items}, {max_items}], got {total_items}")

    if total_calories is None:
        errors.append("Expected total_calories, got None")
    elif not approx_equal(total_calories, expected_total, tol=5.0):
        errors.append(f"Expected total_calories≈{expected_total}, got {total_calories}")

    if not final_message:
        errors.append("Expected non-empty final_message")

    score = 100.0
    if mode != expected_mode:
        score -= 20
    if not (min_items <= total_items <= max_items):
        score -= 25
    if total_calories is None:
        score -= 35
    elif not approx_equal(total_calories, expected_total, tol=5.0):
        score -= 15
    if not final_message:
        score -= 5

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_qa(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []

    final_message = lower_text(get_final_message(response))
    if not final_message:
        errors.append("Expected non-empty final_message")

    score = 100.0
    if not final_message:
        score -= 100

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_guard(case: dict, response: dict) -> tuple[bool, list[str], float]:
    errors = []

    category = case["category"]
    final_message = lower_text(get_final_message(response))

    if case["expected"].get("message_must_not_be_empty") and not final_message:
        errors.append("Expected non-empty final_message")

    semantic_required_categories = {
        "GUARD_EMPTY",
        "GUARD_FOOD_ONLY",
        "GUARD_GIBBERISH",
        "GUARD_NON_ENGLISH",
        "GUARD_QUANTITY_ONLY",
        "GUARD_NON_NUMERIC_QUANTITY",
        "STATE_TOTAL",
    }

    if category in semantic_required_categories:
        if not semantic_guard_match(category, final_message):
            errors.append(
                f"Semantic guard expectation failed for {category}, got '{final_message}'"
            )

    elif category == "STATE_CLEAR":
        if not ("clear" in final_message or "meal" in final_message):
            errors.append(f"Expected clear/meal intent in final_message, got '{final_message}'")

    elif category == "STATE_REMOVE":
        if not ("remove" in final_message or "meal" in final_message or "not" in final_message):
            errors.append(f"Expected remove-related intent in final_message, got '{final_message}'")

    score = 100.0
    if not final_message:
        score -= 50
    if errors:
        score -= 50

    return len(errors) == 0, errors, max(0.0, round(score, 2))


def evaluate_case(case: dict, response: dict) -> tuple[bool, list[str], float]:
    category = case["category"]

    if category == "CAL_SINGLE":
        return evaluate_cal_single(case, response)
    if category == "CAL_MULTI":
        return evaluate_cal_multi(case, response)
    if category == "QA":
        return evaluate_qa(case, response)

    return evaluate_guard(case, response)


# --------------------------------
# Runner
# --------------------------------
def main() -> None:
    rng = random.Random(SEED)
    orchestrator = NutritionOrchestrator()

    cases = build_suite(rng)

    DATASET_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("Running dataset-aligned 400-case evaluation")
    print("=" * 70)
    print(f"Dataset written: {DATASET_OUTPUT_PATH.resolve()}")
    print("=" * 70)

    passed = 0
    failed = 0
    score_sum = 0.0

    category_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "score_sum": 0.0})
    failed_cases = []
    detailed_results = []

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
                },
            }
        )

        if idx % 25 == 0 or idx == len(cases):
            print(f"Progress: {idx}/{len(cases)} | passed={passed} | failed={failed}")

    total_cases = len(cases)
    pass_rate = round((passed / total_cases) * 100.0, 2) if total_cases else 0.0
    average_score = round(score_sum / total_cases, 2) if total_cases else 0.0

    category_rows = []
    for category, stats in sorted(category_stats.items()):
        total = stats["total"]
        category_rows.append(
            {
                "category": category,
                "total": total,
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": round((stats["passed"] / total) * 100.0, 2) if total else 0.0,
                "avg_score": round(stats["score_sum"] / total, 2) if total else 0.0,
            }
        )

    report = {
        "report_name": "dataset_aligned_400_eval",
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

    print("=" * 70)
    print("Nutrition Assistant Dataset-Aligned 400 Evaluation Report")
    print("=" * 70)
    print(f"Total cases     : {total_cases}")
    print(f"Passed cases    : {passed}")
    print(f"Failed cases    : {failed}")
    print(f"Pass rate       : {pass_rate:.2f}%")
    print(f"Average score   : {average_score:.2f}%")
    print(f"Report written  : {REPORT_OUTPUT_PATH.resolve()}")
    print("=" * 70)
    print()
    print("Category breakdown")
    print("=" * 70)
    print(
        f"{'Category':<24}"
        f"{'Total':>8}"
        f"{'Passed':>10}"
        f"{'Failed':>9}"
        f"{'Pass Rate':>14}"
        f"{'Avg Score':>13}"
    )
    print("-" * 78)
    for row in category_rows:
        print(
            f"{row['category']:<24}"
            f"{row['total']:>8}"
            f"{row['passed']:>10}"
            f"{row['failed']:>9}"
            f"{row['pass_rate']:>13.2f}%"
            f"{row['avg_score']:>12.2f}%"
        )
    print("=" * 78)

    if failed_cases:
        print()
        print("Sample failed cases:")
        for case in failed_cases[:20]:
            print(f"- {case['case_id']} [{case['category']}]")
            print(f"    Input: {case['input']}")
            for err in case["errors"]:
                print(f"    * {err}")


if __name__ == "__main__":
    main()