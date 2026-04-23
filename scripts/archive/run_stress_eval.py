import argparse
import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.application.orchestrators.nutrition_orchestrator import NutritionOrchestrator
from src.domain.models.meal_state import MealState


CALORIE_CSV_PATH = Path("data/raw/calories.csv")
DATASET_OUTPUT_PATH = Path("eval/datasets/custom/stress_400_cases.json")
REPORT_OUTPUT_PATH = Path("eval/outputs/stress_400_report.json")


QA_QUESTIONS = [
    "Is avocado healthy?",
    "What are good sources of protein?",
    "Is olive oil good for health?",
    "What foods are rich in vitamin C?",
    "Are eggs healthy?",
    "What are healthy snack ideas?",
    "Is yogurt good for digestion?",
    "What foods are high in fiber?",
    "Is salmon healthy?",
    "What are good sources of iron?",
]

NON_ENGLISH_INPUTS = [
    "سیب ۲۰۰ گرم",
    "برنج ۱۵۰ گرم",
    "موز ۱۰۰ گرم",
    "آووکادو سالمه؟",
    "پروتئین خوب چیه؟",
    "نان ۵۰ گرم",
    "شیر ۲۰۰ گرم",
    "سیب زمینی ۱۲۰ گرم",
    "چی بخورم سالمه؟",
    "این غذا خوبه؟",
]

GIBBERISH_INPUTS = [
    "asdf qwer zxcv",
    "xxxyy 123 ???",
    "blorp flarp",
    "qzxw plmokn",
    "gghh ttrr",
    "zzqv trax",
    "fppp jjjk",
    "wibble wobble",
    "nonsense token",
    "foo bar baz",
]

NOISE_PREFIXES = [
    "hey",
    "please",
    "pls",
    "yo",
    "okay",
    "random text",
    "extra words",
    "hello",
    "hi",
    "bro",
]

CONNECTORS = ["and", "with", "plus", "add"]


def load_foods(csv_path: Path) -> list[str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find calorie CSV at: {csv_path}")

    foods = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            food = (row.get("FoodItem") or "").strip().lower()
            if not food:
                continue
            if not re.fullmatch(r"[a-z0-9][a-z0-9\s\-\+&']*", food):
                continue
            if len(food) < 2:
                continue
            foods.append(food)

    foods = sorted(set(foods))

    # keep foods that are easier for parser / resolver
    filtered = []
    for food in foods:
        words = food.split()
        if len(words) > 4:
            continue
        if any(len(w) == 1 for w in words):
            continue
        filtered.append(food)

    if len(filtered) < 300:
        return foods

    return filtered


def serialize(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [serialize(x) for x in obj]
    if isinstance(obj, tuple):
        return [serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: serialize(v) for k, v in obj.__dict__.items()}
    return str(obj)


def append_conversation_memory(conversation_memory: list[dict], user_text: str, response_obj: Any):
    response = serialize(response_obj)
    entry = {
        "normalized_input": user_text.strip().lower(),
        "kind": response.get("mode", ""),
        "answer": response.get("answer") or response.get("final_message", ""),
        "confidence": response.get("confidence", "LOW"),
        "sources_used": response.get("sources_used", []) or [],
        "retrieved_contexts": response.get("retrieved_contexts", []) or [],
    }
    conversation_memory.append(entry)


def run_turn(
    orchestrator: NutritionOrchestrator,
    user_text: str,
    meal_state: MealState,
    conversation_memory: list[dict],
    history: list[dict],
):
    response_obj = orchestrator.run(
        text=user_text,
        history=history,
        memory_entries=[],
        meal_state=meal_state,
        conversation_memory=conversation_memory,
    )
    response = serialize(response_obj)

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": response.get("final_message", "")})

    append_conversation_memory(conversation_memory, user_text, response_obj)

    return response


def build_single_clean_cases(foods: list[str], rng: random.Random, n: int) -> list[dict]:
    cases = []
    sampled = rng.sample(foods, n)
    for idx, food in enumerate(sampled, start=1):
        grams = rng.choice([50, 75, 100, 120, 150, 180, 200, 250, 300])
        prompt = f"{food} {grams}g"
        cases.append({
            "id": f"ST-SC-{idx:03d}",
            "category": "single_clean",
            "turns": [prompt],
            "expected": {
                "mode": "calorie",
                "total_items": 1,
                "min_matched_items": 1,
            },
        })
    return cases


def build_multi_clean_cases(foods: list[str], rng: random.Random, n: int) -> list[dict]:
    cases = []
    for idx in range(1, n + 1):
        item_count = 2 if idx <= int(n * 0.7) else 3
        chosen = rng.sample(foods, item_count)
        parts = []
        for food in chosen:
            grams = rng.choice([50, 75, 100, 120, 150, 200, 250])
            parts.append(f"{food} {grams}g")
        connector = rng.choice([" and ", " with ", " plus "])
        prompt = connector.join(parts)
        cases.append({
            "id": f"ST-MC-{idx:03d}",
            "category": "multi_clean",
            "turns": [prompt],
            "expected": {
                "mode": "calorie",
                "total_items": item_count,
                "min_matched_items": max(1, item_count - 1),
            },
        })
    return cases


def build_noisy_cases(foods: list[str], rng: random.Random, n: int) -> list[dict]:
    cases = []
    for idx in range(1, n + 1):
        item_count = 2 if idx % 4 != 0 else 3
        chosen = rng.sample(foods, item_count)
        prefix = rng.choice(NOISE_PREFIXES)
        connector = rng.choice(CONNECTORS)

        parts = []
        for i, food in enumerate(chosen):
            grams = rng.choice([60, 90, 100, 130, 170, 210])
            if i == 0 and idx % 3 == 0:
                parts.append(f"{food.replace(' ', '')}{grams}g")
            elif i > 0 and idx % 5 == 0:
                parts.append(f"{food.replace(' ', '')}{grams}g")
            else:
                parts.append(f"{food} {grams}g")

        if idx % 2 == 0:
            prompt = f"{prefix} {parts[0]} {connector} " + f" {connector} ".join(parts[1:])
        else:
            prompt = f"{prefix} " + f"{connector}".join(parts) if idx % 7 == 0 else f"{prefix} " + f" {connector} ".join(parts)

        cases.append({
            "id": f"ST-NO-{idx:03d}",
            "category": "noisy_calorie",
            "turns": [prompt],
            "expected": {
                "mode": "calorie",
                "total_items": item_count,
                "min_matched_items": max(1, item_count - 1),
            },
        })
    return cases


def build_guard_cases(foods: list[str], rng: random.Random, n: int) -> list[dict]:
    cases = []

    quarter = n // 4

    # quantity only
    for idx in range(1, quarter + 1):
        grams = rng.choice([50, 100, 150, 200, 250])
        cases.append({
            "id": f"ST-GQ-{idx:03d}",
            "category": "guard_quantity_only",
            "turns": [f"{grams}g"],
            "expected": {
                "mode": "nutrition_qa",
                "answer_contains_any": ["food name is missing", "provide both the food name"],
            },
        })

    # food only
    sampled_foods = rng.sample(foods, quarter)
    for idx, food in enumerate(sampled_foods, start=1):
        cases.append({
            "id": f"ST-GF-{idx:03d}",
            "category": "guard_food_only",
            "turns": [food],
            "expected": {
                "mode": "nutrition_qa",
                "final_contains_any": ["grams", "200g", "quantity"],
            },
        })

    # quantity not numeric
    word_numbers = [
        "one hundred grams",
        "two hundred grams",
        "three hundred grams",
        "five hundred grams",
        "ten grams",
        "one thousand grams",
        "two grams",
        "six grams",
        "eight grams",
        "nine grams",
    ]
    sampled_foods = rng.sample(foods, quarter)
    for idx, (food, quantity_phrase) in enumerate(zip(sampled_foods, word_numbers), start=1):
        cases.append({
            "id": f"ST-GN-{idx:03d}",
            "category": "guard_quantity_not_numeric",
            "turns": [f"{food} {quantity_phrase}"],
            "expected": {
                "mode": "nutrition_qa",
                "answer_contains_any": ["not written with digits", "write the amount with digits"],
            },
        })

    # non-english / gibberish
    mixed_inputs = NON_ENGLISH_INPUTS[: quarter // 2] + GIBBERISH_INPUTS[: quarter - (quarter // 2)]
    for idx, prompt in enumerate(mixed_inputs, start=1):
        cases.append({
            "id": f"ST-GX-{idx:03d}",
            "category": "guard_mixed_invalid",
            "turns": [prompt],
            "expected": {
                "mode": "nutrition_qa",
                "final_nonempty": True,
            },
        })

    return cases


def build_memory_cases(foods: list[str], rng: random.Random, n: int) -> list[dict]:
    cases = []
    for idx in range(1, n + 1):
        mode = idx % 4

        if mode == 1:
            food1, food2 = rng.sample(foods, 2)
            g1 = rng.choice([100, 150, 200])
            g2 = rng.choice([80, 120, 160])
            turns = [
                f"{food1} {g1}g",
                f"{food2} {g2}g",
                "what is the total now",
            ]
            expected = {"mode": "calorie", "total_items": 2}
            category = "memory_total"

        elif mode == 2:
            food1, food2 = rng.sample(foods, 2)
            g1 = rng.choice([100, 150, 200])
            g2 = rng.choice([80, 120, 160])
            turns = [
                f"{food1} {g1}g",
                f"{food2} {g2}g",
                f"remove {food1}",
                "what is the total now",
            ]
            expected = {"mode": "calorie", "total_items": 1}
            category = "memory_remove"

        elif mode == 3:
            food1, food2 = rng.sample(foods, 2)
            g1 = rng.choice([100, 150, 200])
            g2 = rng.choice([80, 120, 160])
            turns = [
                f"{food1} {g1}g",
                f"{food2} {g2}g",
                "clear meal",
                "what is the total now",
            ]
            expected = {"mode": "calorie", "total_items": 0}
            category = "memory_clear"

        else:
            food1 = rng.choice(foods)
            g1 = rng.choice([100, 150, 200])
            turns = [
                f"{food1} {g1}g",
                f"{food1} {g1}g",
            ]
            expected = {"mode": "calorie", "final_contains_any": ["as i told you before", "already in your current meal", "already answered earlier"]}
            category = "memory_repeat"

        cases.append({
            "id": f"ST-ME-{idx:03d}",
            "category": category,
            "turns": turns,
            "expected": expected,
        })
    return cases


def build_qa_cases(rng: random.Random, n: int) -> list[dict]:
    cases = []
    half = n // 2

    sampled = rng.sample(QA_QUESTIONS, min(len(QA_QUESTIONS), half))
    while len(sampled) < half:
        sampled.append(rng.choice(QA_QUESTIONS))

    for idx, q in enumerate(sampled, start=1):
        cases.append({
            "id": f"ST-QA-{idx:03d}",
            "category": "qa_single",
            "turns": [q],
            "expected": {
                "mode": "nutrition_qa",
                "final_nonempty": True,
            },
        })

    sampled2 = rng.sample(QA_QUESTIONS, min(len(QA_QUESTIONS), n - half))
    while len(sampled2) < (n - half):
        sampled2.append(rng.choice(QA_QUESTIONS))

    for idx, q in enumerate(sampled2, start=1):
        cases.append({
            "id": f"ST-QR-{idx:03d}",
            "category": "qa_repeat",
            "turns": [q, q],
            "expected": {
                "mode": "nutrition_qa",
                "second_final_contains_any": ["as i told you before"],
            },
        })

    return cases


def check_case(case: dict, final_response: dict) -> tuple[bool, list[str]]:
    expected = case["expected"]
    issues = []

    if "mode" in expected:
        if final_response.get("mode") != expected["mode"]:
            issues.append(f"expected mode={expected['mode']}, got {final_response.get('mode')}")

    if "total_items" in expected:
        if final_response.get("total_items") != expected["total_items"]:
            issues.append(f"expected total_items={expected['total_items']}, got {final_response.get('total_items')}")

    if "min_matched_items" in expected:
        matched = final_response.get("matched_items", 0)
        if matched < expected["min_matched_items"]:
            issues.append(
                f"expected matched_items>={expected['min_matched_items']}, got {matched}"
            )

    if expected.get("final_nonempty"):
        final_message = (final_response.get("final_message") or "").strip()
        if not final_message:
            issues.append("expected non-empty final_message")

    if "answer_contains_any" in expected:
        answer = (final_response.get("answer") or "").lower()
        if not any(token.lower() in answer for token in expected["answer_contains_any"]):
            issues.append(
                f"expected answer to contain one of {expected['answer_contains_any']}, got '{final_response.get('answer', '')}'"
            )

    if "final_contains_any" in expected:
        final_message = (final_response.get("final_message") or "").lower()
        if not any(token.lower() in final_message for token in expected["final_contains_any"]):
            issues.append(
                f"expected final_message to contain one of {expected['final_contains_any']}, got '{final_response.get('final_message', '')}'"
            )

    return (len(issues) == 0), issues


def check_repeat_case(case: dict, all_turn_responses: list[dict]) -> tuple[bool, list[str]]:
    expected = case["expected"]
    issues = []

    if "second_final_contains_any" in expected:
        if len(all_turn_responses) < 2:
            issues.append("case expected at least 2 turn responses")
        else:
            second_final = (all_turn_responses[-1].get("final_message") or "").lower()
            if not any(token.lower() in second_final for token in expected["second_final_contains_any"]):
                issues.append(
                    f"expected second final_message to contain one of {expected['second_final_contains_any']}, got '{all_turn_responses[-1].get('final_message', '')}'"
                )

    return (len(issues) == 0), issues


def run_case(orchestrator: NutritionOrchestrator, case: dict) -> dict:
    meal_state = MealState()
    conversation_memory = []
    history = []

    turn_outputs = []
    error = None

    try:
        for turn in case["turns"]:
            response = run_turn(
                orchestrator=orchestrator,
                user_text=turn,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
                history=history,
            )
            turn_outputs.append(response)

        final_response = turn_outputs[-1] if turn_outputs else {}
        ok1, issues1 = check_case(case, final_response)
        ok2, issues2 = check_repeat_case(case, turn_outputs)

        passed = ok1 and ok2
        issues = issues1 + issues2

    except Exception as e:
        passed = False
        issues = [f"exception: {type(e).__name__}: {e}"]
        final_response = {}
        error = f"{type(e).__name__}: {e}"

    return {
        "id": case["id"],
        "category": case["category"],
        "turns": case["turns"],
        "expected": case["expected"],
        "passed": passed,
        "issues": issues,
        "final_response": final_response,
        "all_turn_responses": turn_outputs,
        "error": error,
    }


def build_cases(foods: list[str], seed: int) -> list[dict]:
    rng = random.Random(seed)

    cases = []
    cases.extend(build_single_clean_cases(foods, rng, 120))
    cases.extend(build_multi_clean_cases(foods, rng, 100))
    cases.extend(build_noisy_cases(foods, rng, 80))
    cases.extend(build_guard_cases(foods, rng, 40))
    cases.extend(build_memory_cases(foods, rng, 40))
    cases.extend(build_qa_cases(rng, 20))

    assert len(cases) == 400, f"Expected 400 cases, got {len(cases)}"
    return cases


def summarize(results: list[dict]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    by_category = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    for r in results:
        cat = r["category"]
        by_category[cat]["total"] += 1
        if r["passed"]:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1

    by_category = dict(sorted(by_category.items(), key=lambda x: x[0]))

    failed_cases = [
        {
            "id": r["id"],
            "category": r["category"],
            "issues": r["issues"],
            "turns": r["turns"],
            "final_response": r["final_response"],
        }
        for r in results
        if not r["passed"]
    ]

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "pass_rate": pass_rate,
        "category_breakdown": by_category,
        "failed_case_details": failed_cases,
    }


def print_summary(summary: dict):
    print("=" * 70)
    print("Nutrition Assistant Stress Test Report")
    print("=" * 70)
    print(f"Total cases   : {summary['total_cases']}")
    print(f"Passed cases  : {summary['passed_cases']}")
    print(f"Failed cases  : {summary['failed_cases']}")
    print(f"Pass rate     : {summary['pass_rate']:.2f}%")
    print("=" * 70)
    print("\nCategory breakdown")
    print("=" * 70)
    print(f"{'Category':20} {'Total':>8} {'Passed':>8} {'Failed':>8}")
    print("-" * 70)
    for category, stats in summary["category_breakdown"].items():
        print(f"{category:20} {stats['total']:>8} {stats['passed']:>8} {stats['failed']:>8}")

    if summary["failed_case_details"]:
        print("\nFailed cases")
        print("=" * 70)
        for case in summary["failed_case_details"][:20]:
            print(f"- {case['id']} [{case['category']}]")
            for issue in case["issues"]:
                print(f"    * {issue}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    foods = load_foods(CALORIE_CSV_PATH)
    cases = build_cases(foods, seed=args.seed)

    DATASET_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with DATASET_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    orchestrator = NutritionOrchestrator()
    results = [run_case(orchestrator, case) for case in cases]
    summary = summarize(results)

    report = {
        "seed": args.seed,
        "food_pool_size": len(foods),
        "dataset_path": str(DATASET_OUTPUT_PATH),
        "summary": summary,
        "results": results,
    }

    with REPORT_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_summary(summary)
    print("\nSaved dataset:", DATASET_OUTPUT_PATH)
    print("Saved report :", REPORT_OUTPUT_PATH)


if __name__ == "__main__":
    main()