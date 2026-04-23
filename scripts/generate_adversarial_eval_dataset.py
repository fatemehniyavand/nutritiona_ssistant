import json
import random
from pathlib import Path


SEED = 42
OUTPUT_PATH = Path("eval/datasets/eval_cases_adversarial.json")


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

GRAMS = [50, 75, 100, 120, 150, 200]
NOISE = ["pls", "lol", "uh", "hmm", "maybe", ""]
CONNECTORS = ["and", "add", "with", "plus"]


def kcal(food: str, grams: int) -> float:
    return round((SAFE_FOODS[food] * grams) / 100.0, 2)


def noisy(text: str, rng: random.Random) -> str:
    prefix = rng.choice(NOISE)
    suffix = rng.choice(NOISE)
    return f"{prefix} {text} {suffix}".strip()


def build_adv_single(rng: random.Random, idx: int) -> dict:
    food = rng.choice(list(SAFE_FOODS.keys()))
    grams = rng.choice(GRAMS)

    user_input = rng.choice(
        [
            f"{food} {grams}g",
            f"{food}{grams}g",
            f"add {food} {grams}g",
            f"{food} {grams} g",
            noisy(f"{food} {grams}g", rng),
        ]
    )

    return {
        "case_id": f"ADV-SINGLE-{idx:03d}",
        "category": "ADV",
        "kind": "single_turn",
        "input": user_input,
        "expected": {
            "mode": "calorie",
            "matched_items_min": 1,
            "total_items_min": 1,
            "total_calories": kcal(food, grams),
        },
    }


def build_adv_multi(rng: random.Random, idx: int) -> dict:
    f1, f2 = rng.sample(list(SAFE_FOODS.keys()), 2)
    g1 = rng.choice(GRAMS)
    g2 = rng.choice(GRAMS)
    connector = rng.choice(CONNECTORS)
    total = round(kcal(f1, g1) + kcal(f2, g2), 2)

    user_input = rng.choice(
        [
            f"{f1} {g1}g {connector} {f2} {g2}g",
            f"{f1}{g1}g {connector} {f2}{g2}g",
            f"{f1} {g1} g {connector} {f2} {g2} g",
            noisy(f"{f1} {g1}g {connector} {f2} {g2}g", rng),
        ]
    )

    return {
        "case_id": f"ADV-MULTI-{idx:03d}",
        "category": "ADV",
        "kind": "single_turn",
        "input": user_input,
        "expected": {
            "mode": "calorie",
            "matched_items_min": 1,
            "total_items_min": 1,
            "total_calories": total,
        },
    }


def build_adv_guard_cases() -> list[dict]:
    raw = [
        "",
        "200g",
        "apple two hundred grams",
        "سلام خوبی",
        "asdkjhasd qweoiu",
        "zzzz food blahhhh",
        "what is the total now?",
        "clear meal",
        "remove apple 100g",
        "ciao come stai",
    ]

    cases = []
    for i, user_input in enumerate(raw, start=1):
        cases.append(
            {
                "case_id": f"ADV-GUARD-{i:03d}",
                "category": "ADV",
                "kind": "single_turn",
                "input": user_input,
                "expected": {
                    "message_non_empty": True,
                },
            }
        )
    return cases


def main() -> None:
    rng = random.Random(SEED)

    cases = []
    for i in range(1, 21):
        cases.append(build_adv_single(rng, i))

    for i in range(1, 21):
        cases.append(build_adv_multi(rng, i))

    cases.extend(build_adv_guard_cases())

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} adversarial evaluation cases at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()