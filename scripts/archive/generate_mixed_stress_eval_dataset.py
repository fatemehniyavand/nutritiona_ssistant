import json
import random
import re
from pathlib import Path

import pandas as pd


SEED = 42
TOTAL_CASES = 400

DATA_PATH = Path("data/processed/calories_cleaned.csv")
OUTPUT_PATH = Path("eval/datasets/eval_cases_mixed_stress.json")


def slugify(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9\s\-&()]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
        food_item = str(row["food_item"]).strip()
        food_key = str(row["food_key"]).strip()
        calories = float(row["calories_per_100g"])

        if not food_item or not food_key:
            continue

        normalized = slugify(food_item)
        if normalized in seen:
            continue
        seen.add(normalized)

        foods.append(
            {
                "food_item": food_item,
                "food_key": food_key,
                "normalized_food_item": normalized,
                "calories_per_100g": calories,
            }
        )

    if len(foods) < 500:
        raise RuntimeError(
            f"Too few usable foods loaded: {len(foods)}. Expected a richer dataset."
        )

    return foods


def random_grams(rng: random.Random) -> int:
    return rng.choice([50, 75, 80, 90, 100, 120, 150, 180, 200, 250, 300])


def calc_calories(calories_per_100g: float, grams: float) -> float:
    return round((calories_per_100g * grams) / 100.0, 2)


def mutate_food_name(food_name: str, rng: random.Random) -> str:
    """
    Mild noise that should often still be recoverable by a decent normalizer/parser.
    """
    s = food_name.lower().strip()

    mutations = [
        lambda x: x.replace(" ", ""),
        lambda x: x.replace(" ", "  "),
        lambda x: x.replace("a", "aa", 1) if "a" in x else x,
        lambda x: x[:-1] if len(x) > 5 else x,
        lambda x: x + " ",
        lambda x: " " + x,
        lambda x: x.replace("-", " "),
        lambda x: x.replace("&", " and "),
        lambda x: x.replace(" ", "-"),
    ]

    candidate = rng.choice(mutations)(s)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    return candidate or s


def make_ood_food(base_name: str, rng: random.Random, known_names: set[str]) -> str:
    """
    Produce an out-of-dataset item that should not exactly exist in DB.
    """
    prefixes = [
        "mystic",
        "quantum",
        "lava",
        "shadow",
        "crystal",
        "ultra",
        "wild",
        "fake",
        "dream",
        "cosmic",
    ]
    suffixes = [
        "delight",
        "bites",
        "mix",
        "fusion",
        "snack",
        "supreme",
        "surprise",
        "blend",
        "special",
        "burger",
    ]

    base = slugify(base_name).replace(" ", "_")
    for _ in range(50):
        candidate = f"{rng.choice(prefixes)} {base.split('_')[0]} {rng.choice(suffixes)}"
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if slugify(candidate) not in known_names:
            return candidate

    return f"unknown {base.split('_')[0]} item"


def build_exact_case(case_id: int, food: dict, rng: random.Random) -> dict:
    grams = random_grams(rng)
    expected_calories = calc_calories(food["calories_per_100g"], grams)

    return {
        "case_id": f"MIX-EXACT-{case_id:03d}",
        "category": "MIX_EXACT",
        "input": f"{food['food_item'].lower()} {grams}g",
        "expected": {
            "mode": "calorie_input",
            "total_items": 1,
            "matched_items": 1,
            "coverage": 1.0,
            "total_calories": expected_calories,
        },
        "meta": {
            "food_item": food["food_item"],
            "grams": grams,
            "in_dataset": True,
            "noise": False,
            "multi_item": False,
            "ood": False,
        },
    }


def build_noisy_case(case_id: int, food: dict, rng: random.Random) -> dict:
    grams = random_grams(rng)
    noisy_name = mutate_food_name(food["food_item"], rng)
    expected_calories = calc_calories(food["calories_per_100g"], grams)

    styles = [
        f"{noisy_name}{grams}g",
        f"{noisy_name} {grams} g",
        f"add {noisy_name} {grams}g",
        f"{noisy_name}   {grams}g",
    ]
    user_input = rng.choice(styles)

    return {
        "case_id": f"MIX-NOISE-{case_id:03d}",
        "category": "MIX_NOISE",
        "input": user_input,
        "expected": {
            "mode": "calorie_input",
            "total_items": 1,
            "matched_items_min": 0,
            "matched_items_max": 1,
            "coverage_min": 0.0,
            "coverage_max": 1.0,
            "reference_total_calories_if_matched": expected_calories,
        },
        "meta": {
            "food_item": food["food_item"],
            "noisy_food_item": noisy_name,
            "grams": grams,
            "in_dataset": True,
            "noise": True,
            "multi_item": False,
            "ood": False,
        },
    }


def build_multi_mixed_case(case_id: int, foods: list[dict], rng: random.Random, known_names: set[str]) -> dict:
    known_a = rng.choice(foods)
    known_b = rng.choice(foods)
    while known_b["normalized_food_item"] == known_a["normalized_food_item"]:
        known_b = rng.choice(foods)

    include_ood = rng.random() < 0.5

    grams_a = random_grams(rng)
    grams_b = random_grams(rng)

    item_a = mutate_food_name(known_a["food_item"], rng) if rng.random() < 0.4 else known_a["food_item"].lower()
    item_b = mutate_food_name(known_b["food_item"], rng) if rng.random() < 0.4 else known_b["food_item"].lower()

    parts = [
        f"{item_a} {grams_a}g",
        f"{item_b} {grams_b}g",
    ]

    expected_matched = 2
    expected_total_calories = (
        calc_calories(known_a["calories_per_100g"], grams_a)
        + calc_calories(known_b["calories_per_100g"], grams_b)
    )

    meta_items = [
        {
            "food_item": known_a["food_item"],
            "grams": grams_a,
            "in_dataset": True,
        },
        {
            "food_item": known_b["food_item"],
            "grams": grams_b,
            "in_dataset": True,
        },
    ]

    if include_ood:
        ood_food = make_ood_food(known_b["food_item"], rng, known_names)
        grams_c = random_grams(rng)
        parts.append(f"{ood_food} {grams_c}g")
        meta_items.append(
            {
                "food_item": ood_food,
                "grams": grams_c,
                "in_dataset": False,
            }
        )

    connector = rng.choice([" and ", " plus ", " with ", " and add "])
    user_input = connector.join(parts)

    return {
        "case_id": f"MIX-MULTI-{case_id:03d}",
        "category": "MIX_MULTI",
        "input": user_input,
        "expected": {
            "mode": "calorie_input",
            "total_items": len(parts),
            "matched_items_min": expected_matched,
            "matched_items_max": len(parts),
            "coverage_min": round(expected_matched / len(parts), 2),
            "coverage_max": 1.0,
            "reference_known_total_calories": round(expected_total_calories, 2),
        },
        "meta": {
            "items": meta_items,
            "noise": any("  " in p or "-" in p for p in parts),
            "multi_item": True,
            "ood": include_ood,
        },
    }


def build_ood_case(case_id: int, foods: list[dict], rng: random.Random, known_names: set[str]) -> dict:
    base = rng.choice(foods)
    grams = random_grams(rng)
    ood_food = make_ood_food(base["food_item"], rng, known_names)

    styles = [
        f"{ood_food} {grams}g",
        f"add {ood_food} {grams}g",
        f"{ood_food}{grams}g",
    ]

    return {
        "case_id": f"MIX-OOD-{case_id:03d}",
        "category": "MIX_OOD",
        "input": rng.choice(styles),
        "expected": {
            "mode": "calorie_input",
            "total_items": 1,
            "matched_items_min": 0,
            "matched_items_max": 1,
            "coverage_min": 0.0,
            "coverage_max": 1.0,
        },
        "meta": {
            "base_food_item": base["food_item"],
            "ood_food_item": ood_food,
            "grams": grams,
            "in_dataset": False,
            "noise": False,
            "multi_item": False,
            "ood": True,
        },
    }


def main() -> None:
    rng = random.Random(SEED)
    foods = load_foods()
    known_names = {f["normalized_food_item"] for f in foods}

    exact_count = 140
    noisy_count = 100
    multi_count = 100
    ood_count = 60

    assert exact_count + noisy_count + multi_count + ood_count == TOTAL_CASES

    cases = []
    cursor = 1

    for _ in range(exact_count):
        food = rng.choice(foods)
        cases.append(build_exact_case(cursor, food, rng))
        cursor += 1

    for _ in range(noisy_count):
        food = rng.choice(foods)
        cases.append(build_noisy_case(cursor, food, rng))
        cursor += 1

    for _ in range(multi_count):
        cases.append(build_multi_mixed_case(cursor, foods, rng, known_names))
        cursor += 1

    for _ in range(ood_count):
        cases.append(build_ood_case(cursor, foods, rng, known_names))
        cursor += 1

    rng.shuffle(cases)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} mixed stress evaluation cases at {OUTPUT_PATH}")

    by_cat = {}
    for case in cases:
        by_cat[case["category"]] = by_cat.get(case["category"], 0) + 1

    print("Category breakdown:")
    for k, v in sorted(by_cat.items()):
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()