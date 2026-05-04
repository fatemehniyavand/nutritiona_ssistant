import json
import random
from pathlib import Path


SEED = 42
OUTPUT_PATH = Path("eval/datasets/eval_cases.json")


SAFE_FOODS = {
    "apple": 52.0,
    "banana": 89.0,
    "milk": 61.0,
    "rice": 130.0,
    "bread": 265.0,
    "egg": 155.0,
    "avocado": 160.0,
    "oats": 389.0,
    "pizza": 266.0,
    "grilled chicken": 165.0,
}


QA_QUESTIONS = [
    "What are good sources of protein?",
    "Is avocado healthy?",
    "What foods are high in fiber?",
    "Why is hydration important?",
    "Are eggs healthy?",
    "What are healthy breakfast ideas?",
    "Is brown rice better than white rice?",
    "Why are vegetables important?",
    "What foods help with satiety?",
    "How much water should a person drink?",
]


GRAMS = [50, 75, 100, 120, 150, 200, 250]


def kcal(food: str, grams: int) -> float:
    return round((SAFE_FOODS[food] * grams) / 100.0, 2)


def single_variants(food: str, grams: int) -> list[str]:
    return [
        f"{food} {grams}g",
        f"{food}{grams}g",
        f"add {food} {grams}g",
        f"{food} {grams} g",
    ]


def multi_variants(items: list[tuple[str, int]]) -> list[str]:
    a_food, a_grams = items[0]
    b_food, b_grams = items[1]

    base = [
        f"{a_food} {a_grams}g and {b_food} {b_grams}g",
        f"{a_food}{a_grams}g and {b_food}{b_grams}g",
        f"add {a_food} {a_grams}g and {b_food} {b_grams}g",
    ]

    if len(items) == 3:
        c_food, c_grams = items[2]
        base.extend(
            [
                f"{a_food} {a_grams}g and {b_food} {b_grams}g and {c_food} {c_grams}g",
                f"add {a_food} {a_grams}g and {b_food} {b_grams}g and {c_food} {c_grams}g",
            ]
        )

    return base


def build_cal_cases(rng: random.Random, count: int = 30) -> list[dict]:
    foods = list(SAFE_FOODS.keys())
    cases = []

    for i in range(1, count + 1):
        food = rng.choice(foods)
        grams = rng.choice(GRAMS)
        user_input = rng.choice(single_variants(food, grams))

        cases.append(
            {
                "case_id": f"CAL-{i:03d}",
                "category": "CAL",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "matched_items": 1,
                    "total_items": 1,
                    "coverage": 1.0,
                    "total_calories": kcal(food, grams),
                },
                "meta": {
                    "food": food,
                    "grams": grams,
                },
            }
        )

    return cases


def build_guard_cases() -> list[dict]:
    raw = [
        ("GRD-001", "", "empty"),
        ("GRD-002", "   ", "empty"),
        ("GRD-003", "200g", "quantity_only"),
        ("GRD-004", "150 g", "quantity_only"),
        ("GRD-005", "apple", "food_only"),
        ("GRD-006", "banana", "food_only"),
        ("GRD-007", "apple two hundred grams", "non_numeric_quantity"),
        ("GRD-008", "banana one hundred grams", "non_numeric_quantity"),
        ("GRD-009", "سلام خوبی", "non_english"),
        ("GRD-010", "ciao come stai", "non_english"),
        ("GRD-011", "asdkjhasd qweoiu zmxn", "gibberish"),
        ("GRD-012", "zzzz food blahhhh", "gibberish"),
        ("GRD-013", "what is the total now?", "state_total"),
        ("GRD-014", "clear meal", "state_clear"),
        ("GRD-015", "remove apple 100g", "state_remove"),
        ("GRD-016", "reset meal", "state_clear"),
        ("GRD-017", "delete meal", "state_clear"),
        ("GRD-018", "meal total", "state_total"),
        ("GRD-019", "take out banana 100g", "state_remove"),
        ("GRD-020", "whats the total now", "state_total"),
    ]

    cases = []
    for case_id, user_input, semantic in raw:
        cases.append(
            {
                "case_id": case_id,
                "category": "GRD",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "message_non_empty": True,
                    "semantic_guard": semantic,
                },
            }
        )
    return cases


def build_memory_cases(rng: random.Random, count: int = 15) -> list[dict]:
    foods = list(SAFE_FOODS.keys())
    cases = []

    for i in range(1, count + 1):
        f1, f2 = rng.sample(foods, 2)
        g1 = rng.choice(GRAMS)
        g2 = rng.choice(GRAMS)

        total = round(kcal(f1, g1) + kcal(f2, g2), 2)

        steps = [
            f"{f1} {g1}g",
            f"and {f2} {g2}g",
            "what is the total now?",
        ]

        cases.append(
            {
                "case_id": f"MEM-{i:03d}",
                "category": "MEM",
                "kind": "multi_turn",
                "steps": steps,
                "expected": {
                    "final_mode": "calorie",
                    "meal_total": total,
                    "matched_items": 2,
                },
                "meta": {
                    "foods": [(f1, g1), (f2, g2)],
                },
            }
        )

    return cases


def build_multi_cases(rng: random.Random, count: int = 25) -> list[dict]:
    foods = list(SAFE_FOODS.keys())
    cases = []

    for i in range(1, count + 1):
        item_count = 2 if i <= 18 else 3
        picked = rng.sample(foods, item_count)

        items = []
        total = 0.0
        for food in picked:
            grams = rng.choice(GRAMS)
            items.append((food, grams))
            total += kcal(food, grams)

        user_input = rng.choice(multi_variants(items))

        cases.append(
            {
                "case_id": f"MUL-{i:03d}",
                "category": "MUL",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "matched_items": item_count,
                    "total_items": item_count,
                    "coverage": 1.0,
                    "total_calories": round(total, 2),
                },
                "meta": {
                    "items": items,
                },
            }
        )

    return cases


def build_qa_cases(rng: random.Random, count: int = 10) -> list[dict]:
    questions = QA_QUESTIONS[:]
    rng.shuffle(questions)

    cases = []
    for i in range(1, count + 1):
        q = questions[i - 1]
        cases.append(
            {
                "case_id": f"QA-{i:03d}",
                "category": "QA",
                "kind": "single_turn",
                "input": q,
                "expected": {
                    "message_non_empty": True,
                    "mode_candidates": ["qa", "nutrition_qa", "unknown"],
                },
            }
        )
    return cases


def main() -> None:
    rng = random.Random(SEED)

    cases = []
    cases.extend(build_cal_cases(rng, 30))
    cases.extend(build_guard_cases())
    cases.extend(build_memory_cases(rng, 15))
    cases.extend(build_multi_cases(rng, 25))
    cases.extend(build_qa_cases(rng, 10))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()