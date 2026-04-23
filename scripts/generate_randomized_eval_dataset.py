import json
import random
from pathlib import Path


SEED = 42
OUTPUT_PATH = Path("eval/datasets/eval_cases_randomized.json")


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
]

GRAMS = [50, 75, 100, 120, 150, 200, 250]


def kcal(food: str, grams: int) -> float:
    return round((SAFE_FOODS[food] * grams) / 100.0, 2)


def build_random_case(rng: random.Random, idx: int) -> dict:
    mode = rng.choice(["single", "multi", "qa", "guard"])

    if mode == "single":
        food = rng.choice(list(SAFE_FOODS.keys()))
        grams = rng.choice(GRAMS)
        user_input = rng.choice(
            [
                f"{food} {grams}g",
                f"{food}{grams}g",
                f"add {food} {grams}g",
            ]
        )
        return {
            "case_id": f"RND-{idx:03d}",
            "category": "RND",
            "kind": "single_turn",
            "input": user_input,
            "expected": {
                "mode": "calorie",
                "matched_items_min": 1,
                "total_items_min": 1,
                "total_calories": kcal(food, grams),
            },
        }

    if mode == "multi":
        foods = rng.sample(list(SAFE_FOODS.keys()), 2)
        g1 = rng.choice(GRAMS)
        g2 = rng.choice(GRAMS)
        total = round(kcal(foods[0], g1) + kcal(foods[1], g2), 2)
        user_input = rng.choice(
            [
                f"{foods[0]} {g1}g and {foods[1]} {g2}g",
                f"add {foods[0]} {g1}g and {foods[1]} {g2}g",
                f"{foods[0]}{g1}g and {foods[1]}{g2}g",
            ]
        )
        return {
            "case_id": f"RND-{idx:03d}",
            "category": "RND",
            "kind": "single_turn",
            "input": user_input,
            "expected": {
                "mode": "calorie",
                "matched_items_min": 1,
                "total_items_min": 1,
                "total_calories": total,
            },
        }

    if mode == "qa":
        q = rng.choice(QA_QUESTIONS)
        return {
            "case_id": f"RND-{idx:03d}",
            "category": "RND",
            "kind": "single_turn",
            "input": q,
            "expected": {
                "message_non_empty": True,
            },
        }

    guard_input = rng.choice(
        [
            "",
            "200g",
            "banana",
            "apple two hundred grams",
            "سلام خوبی",
            "asdkjhasd",
        ]
    )
    return {
        "case_id": f"RND-{idx:03d}",
        "category": "RND",
        "kind": "single_turn",
        "input": guard_input,
        "expected": {
            "message_non_empty": True,
        },
    }


def main() -> None:
    rng = random.Random(SEED)

    cases = [build_random_case(rng, i) for i in range(1, 201)]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} randomized evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()