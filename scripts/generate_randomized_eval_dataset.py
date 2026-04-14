import json
import os
import random

OUTPUT_PATH = "eval/datasets/eval_cases_randomized.json"


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


FOODS = [
    ("apple", 52),
    ("banana", 89),
    ("milk", 61),
    ("brown rice", 111),
    ("rice", 130),
    ("chicken", 165),
    ("grilled chicken", 165),
    ("egg", 155),
    ("avocado", 160),
    ("oats", 389),
    ("bread", 265),
]

OOD_FOODS = [
    "unicorn milk",
    "dragon meat",
    "quantum rice",
    "alien fruit",
    "ghost food",
    "space burger",
    "mars protein",
]

NOISE_PREFIXES = [
    "",
    "please ",
    "pls ",
    "hello ",
    "hi ",
    "hey ",
    "i want ",
]

CONNECTORS = [
    " and ",
    " plus ",
    " with ",
    " ",
]

GRAMS = [50, 100, 150, 200]


def make_single_calorie_case(idx: int):
    food, kcal = random.choice(FOODS)
    grams = random.choice(GRAMS)
    prefix = random.choice(NOISE_PREFIXES)

    text = f"{prefix}{food} {grams}g".strip()
    total = round(kcal * grams / 100, 2)

    total_items = 1 if prefix.strip() == "" else 2 if prefix.strip() in {"hello", "hi", "hey", "please", "pls", "i want"} else 1

    # To keep randomized tests stable, use a range and avoid total_items for noisy cases.
    expected = {
        "mode": "calorie",
        "matched_items": 1,
        "min_total_calories": max(0.0, total - 0.01),
        "max_total_calories": total + 0.01,
    }

    return case(f"RND-CAL-{idx:03}", "single_turn", expected, text)


def make_multi_calorie_case(idx: int):
    n = random.choice([2, 3, 4])
    selected = random.sample(FOODS, n)
    connector = random.choice(CONNECTORS)

    parts = []
    total = 0.0
    for food, kcal in selected:
        grams = random.choice(GRAMS)
        parts.append(f"{food} {grams}g")
        total += kcal * grams / 100

    text = connector.join(parts).strip()
    total = round(total, 2)

    expected = {
        "mode": "calorie",
        "matched_items": n,
        "total_items": n,
        "min_total_calories": max(0.0, total - 0.01),
        "max_total_calories": total + 0.01,
    }

    return case(f"RND-MUL-{idx:03}", "single_turn", expected, text)


def make_ood_case(idx: int):
    food = random.choice(OOD_FOODS)
    grams = random.choice(GRAMS)
    text = f"{food} {grams}g"

    expected = {
        "mode": "calorie",
        "matched_items": 0,
        "confidence_in": ["LOW"],
    }

    return case(f"RND-OOD-{idx:03}", "single_turn", expected, text)


def make_guard_case(idx: int):
    samples = [
        ("", {"mode": "nutrition_qa", "answer_contains": "empty"}),
        ("   ", {"mode": "nutrition_qa", "answer_contains": "empty"}),
        ("apple two hundred grams", {"mode": "nutrition_qa", "answer_contains": "digits"}),
        ("200g", {"mode": "nutrition_qa", "answer_contains": "food name"}),
        ("apple", {"mode": "nutrition_qa", "answer_contains": "quantity"}),
        ("سلام", {"mode": "nutrition_qa", "answer_contains": "english"}),
    ]
    text, expected = random.choice(samples)
    return case(f"RND-GRD-{idx:03}", "single_turn", expected, text)


def make_memory_case(idx: int):
    food1, kcal1 = random.choice(FOODS)
    food2, kcal2 = random.choice([f for f in FOODS if f[0] != food1])

    g1 = random.choice(GRAMS)
    g2 = random.choice(GRAMS)

    total = round((kcal1 * g1 / 100) + (kcal2 * g2 / 100), 2)

    steps = [
        f"{food1} {g1}g",
        f"{food2} {g2}g",
        "what is the total now?",
    ]

    expected = {
        "final_mode": "calorie",
        "meal_total": total,
    }

    return case(f"RND-MEM-{idx:03}", "multi_turn", expected, steps=steps)


def main():
    random.seed(12345)

    cases = []

    # 60 single calorie
    for i in range(1, 61):
        cases.append(make_single_calorie_case(i))

    # 60 multi calorie
    for i in range(1, 61):
        cases.append(make_multi_calorie_case(i))

    # 30 OOD
    for i in range(1, 31):
        cases.append(make_ood_case(i))

    # 25 guard
    for i in range(1, 26):
        cases.append(make_guard_case(i))

    # 25 memory
    for i in range(1, 26):
        cases.append(make_memory_case(i))

    assert len(cases) == 200, f"Expected 200 randomized cases, got {len(cases)}"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} randomized evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()