import json
import os
import random

BASE_PATH = "eval/datasets/eval_cases.json"
OUTPUT_PATH = "eval/datasets/eval_cases_extended.json"


def load_base():
    with open(BASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def case(case_id, case_type, expected, input_text=None, steps=None):
    payload = {
        "id": case_id,
        "type": case_type,
        "expected": expected,
    }
    if input_text is not None:
        payload["input"] = input_text
    if steps is not None:
        payload["steps"] = steps
    return payload


def real_user_cases():
    """
    40 noisy / realistic user-log style cases.
    Expectations are aligned with current parser + calorie pipeline behavior.
    """
    templates = [
        (
            "banana 100 g milk 200 g",
            {
                "mode": "calorie",
                "matched_items": 2,
                "total_items": 2,
                "min_total_calories": 210.0,
                "max_total_calories": 212.0,
            },
        ),
        (
            "rice100gandmilk200g",
            {
                "mode": "calorie",
                "matched_items": 2,
                "total_items": 2,
                "min_total_calories": 250.0,
                "max_total_calories": 252.0,
            },
        ),
        (
            "banana100gandmilk150g",
            {
                "mode": "calorie",
                "matched_items": 2,
                "total_items": 2,
                "min_total_calories": 178.0,
                "max_total_calories": 181.0,
            },
        ),
        (
            "add apple 200g then banana 100g",
            {
                "mode": "calorie",
                "matched_items": 2,
                "total_items": 3,
                "min_total_calories": 193.0,
                "max_total_calories": 193.0,
            },
        ),
        (
            "apple two hundred grams",
            {
                "mode": "nutrition_qa",
                "answer_contains": "digits",
            },
        ),
        (
            "hello add banana 100g",
            {
                "mode": "calorie",
                "matched_items": 1,
                "total_items": 2,
                "min_total_calories": 85.0,
                "max_total_calories": 95.0,
            },
        ),
        (
            "pls apple200g",
            {
                "mode": "calorie",
                "matched_items": 1,
                "total_items": 1,
                "min_total_calories": 100.0,
                "max_total_calories": 110.0,
            },
        ),
        (
            "milk 200g and random text",
            {
                "mode": "calorie",
                "matched_items": 1,
                "total_items": 2,
                "min_total_calories": 120.0,
                "max_total_calories": 124.0,
            },
        ),
        (
            "i want apple 200g",
            {
                "mode": "calorie",
                "matched_items": 1,
                "total_items": 2,
                "min_total_calories": 100.0,
                "max_total_calories": 110.0,
            },
        ),
        (
            "apple 200g pls fast",
            {
                "mode": "calorie",
                "matched_items": 1,
                "total_items": 2,
                "min_total_calories": 100.0,
                "max_total_calories": 110.0,
            },
        ),
    ]

    cases = []
    repeated = templates * 4
    assert len(repeated) == 40

    for i, (text, expected) in enumerate(repeated, 1):
        cases.append(case(f"LOG-{i:03}", "single_turn", expected, text))

    return cases


def stress_cases(n=30):
    foods = [
        ("apple", 52),
        ("banana", 89),
        ("milk", 61),
        ("rice", 130),
        ("chicken", 165),
        ("egg", 155),
        ("bread", 265),
        ("avocado", 160),
    ]

    cases = []

    for i in range(n):
        selected = random.sample(foods, random.randint(3, 6))

        parts = []
        total = 0.0

        for name, kcal in selected:
            grams = random.choice([50, 100, 150, 200])
            parts.append(f"{name} {grams}g")
            total += kcal * grams / 100

        text = " ".join(parts)

        cases.append(
            case(
                f"STR-{i+1:03}",
                "single_turn",
                {
                    "mode": "calorie",
                    "matched_items": len(selected),
                    "total_items": len(selected),
                    "min_total_calories": round(total - 30, 2),
                    "max_total_calories": round(total + 30, 2),
                },
                text,
            )
        )

    return cases


def ood_cases(n=30):
    unknowns = [
        "dragon meat",
        "unicorn milk",
        "alien fruit",
        "mars protein",
        "ghost food",
        "space burger",
        "quantum rice",
    ]

    cases = []

    for i in range(n):
        food = random.choice(unknowns)
        grams = random.choice([50, 100, 150, 200])

        cases.append(
            case(
                f"OOD-{i+1:03}",
                "single_turn",
                {
                    "mode": "calorie",
                    "matched_items": 0,
                    "confidence_in": ["LOW"],
                },
                f"{food} {grams}g",
            )
        )

    return cases


def main():
    random.seed(42)

    base = load_base()
    logs = real_user_cases()
    stress = stress_cases(30)
    ood = ood_cases(30)

    extended_only = logs + stress + ood
    assert len(extended_only) == 100, f"Expected 100 extended cases, got {len(extended_only)}"

    full = base + extended_only

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2, ensure_ascii=False)

    print(f"Base cases     : {len(base)}")
    print(f"Extended cases : {len(extended_only)}")
    print(f"Total cases    : {len(full)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()