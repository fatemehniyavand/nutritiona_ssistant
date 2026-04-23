import json
import random
from pathlib import Path


SEED = 42
BASE_PATH = Path("eval/datasets/eval_cases.json")
OUTPUT_PATH = Path("eval/datasets/eval_cases_extended.json")


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

GRAMS = [50, 75, 100, 120, 150, 200, 250]


def kcal(food: str, grams: int) -> float:
    return round((SAFE_FOODS[food] * grams) / 100.0, 2)


def build_log_cases(rng: random.Random, count: int = 40) -> list[dict]:
    foods = list(SAFE_FOODS.keys())
    cases = []

    for i in range(1, count + 1):
        f1, f2 = rng.sample(foods, 2)
        g1 = rng.choice(GRAMS)
        g2 = rng.choice(GRAMS)
        total = round(kcal(f1, g1) + kcal(f2, g2), 2)

        steps = [
            f"{f1} {g1}g",
            f"add {f2} {g2}g",
            "what is the total now?",
        ]

        cases.append(
            {
                "case_id": f"LOG-{i:03d}",
                "category": "LOG",
                "kind": "multi_turn",
                "steps": steps,
                "expected": {
                    "final_mode": "calorie",
                    "meal_total": total,
                    "matched_items": 2,
                    "message_non_empty": True,
                },
            }
        )

    return cases


def build_ood_cases(rng: random.Random, count: int = 30) -> list[dict]:
    ood_foods = [
        "dragon burger",
        "quantum soup",
        "lava rice",
        "shadow pizza",
        "cosmic oats",
        "mystic milkshake",
        "ultra banana fusion",
        "wild apple burger",
        "crystal chicken bites",
        "fake avocado supreme",
    ]

    cases = []
    for i in range(1, count + 1):
        food = rng.choice(ood_foods)
        grams = rng.choice(GRAMS)
        user_input = rng.choice(
            [
                f"{food} {grams}g",
                f"add {food} {grams}g",
                f"{food}{grams}g",
            ]
        )

        cases.append(
            {
                "case_id": f"OOD-{i:03d}",
                "category": "OOD",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "matched_items_max": 1,
                    "coverage_max": 1.0,
                    "message_non_empty": True,
                },
            }
        )

    return cases


def build_stress_cases(rng: random.Random, count: int = 30) -> list[dict]:
    foods = list(SAFE_FOODS.keys())
    cases = []

    for i in range(1, count + 1):
        item_count = rng.choice([3, 4, 5])
        picked = rng.sample(foods, item_count)

        parts = []
        total = 0.0
        for food in picked:
            grams = rng.choice(GRAMS)
            parts.append(f"{food} {grams}g")
            total += kcal(food, grams)

        user_input = " and ".join(parts)

        cases.append(
            {
                "case_id": f"STR-{i:03d}",
                "category": "STR",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "mode": "calorie",
                    "matched_items": item_count,
                    "total_items": item_count,
                    "total_calories": round(total, 2),
                    "coverage": 1.0,
                },
            }
        )

    return cases


def main() -> None:
    rng = random.Random(SEED)

    if not BASE_PATH.exists():
        raise FileNotFoundError(
            f"{BASE_PATH} not found. Run generate_eval_dataset.py first."
        )

    with BASE_PATH.open("r", encoding="utf-8") as f:
        base_cases = json.load(f)

    extended_cases = []
    extended_cases.extend(build_log_cases(rng, 40))
    extended_cases.extend(build_ood_cases(rng, 30))
    extended_cases.extend(build_stress_cases(rng, 30))

    all_cases = base_cases + extended_cases

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=2, ensure_ascii=False)

    print(f"Base cases     : {len(base_cases)}")
    print(f"Extended cases : {len(extended_cases)}")
    print(f"Total cases    : {len(all_cases)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()