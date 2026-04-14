from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RAW_PATH = Path("data/raw/calories.csv")
OUTPUT_PATH = Path("data/processed/calories_cleaned.csv")


def normalize_text(value) -> str | None:
    """
    Normalize text fields:
    - convert to string
    - strip surrounding spaces
    - collapse repeated spaces
    - lowercase
    - return None for empty/null-like values
    """
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"\s+", " ", text)
    return text.lower()


def parse_numeric(value) -> float | None:
    """
    Parse values like:
    - '52 cal'
    - '260 kJ'
    - '52'
    - '52,3'
    - None / NaN
    Returns float or None.
    """
    if pd.isna(value):
        return None

    text = str(value).strip().lower()
    if not text:
        return None

    text = text.replace(",", ".")
    text = text.replace("kcal", "")
    text = text.replace("cal", "")
    text = text.replace("kj", "")
    text = text.strip()

    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def build_food_key(food_item: str | None) -> str | None:
    """
    Create a normalized retrieval key.
    Example:
    'Chicken Breast, Raw' -> 'chicken_breast_raw'
    """
    if not food_item:
        return None

    key = food_item.lower().strip()
    key = re.sub(r"[^a-z0-9\s]+", " ", key)
    key = re.sub(r"\s+", "_", key).strip("_")
    return key or None


def clean_calorie_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected raw columns:
    - FoodCategory
    - FoodItem
    - per100grams
    - Cals_per100grams
    - KJ_per100grams

    Output cleaned columns:
    - food_category
    - food_item
    - food_key
    - serving_reference_g
    - calories_per_100g
    - kj_per_100g
    """
    column_mapping = {
        "FoodCategory": "food_category",
        "FoodItem": "food_item",
        "per100grams": "serving_reference_g",
        "Cals_per100grams": "calories_per_100g",
        "KJ_per100grams": "kj_per_100g",
    }

    missing_cols = [col for col in column_mapping if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected columns in CSV: {missing_cols}")

    df = df.rename(columns=column_mapping).copy()

    # Normalize text columns
    df["food_category"] = df["food_category"].apply(normalize_text)
    df["food_item"] = df["food_item"].apply(normalize_text)

    # Parse numeric columns
    df["serving_reference_g"] = df["serving_reference_g"].apply(parse_numeric)
    df["calories_per_100g"] = df["calories_per_100g"].apply(parse_numeric)
    df["kj_per_100g"] = df["kj_per_100g"].apply(parse_numeric)

    # Default serving reference to 100 if missing
    df["serving_reference_g"] = df["serving_reference_g"].fillna(100.0)

    # Build normalized key
    df["food_key"] = df["food_item"].apply(build_food_key)

    # Drop rows with no usable food name
    df = df[df["food_item"].notna()].copy()

    # Drop rows with no calorie value
    df = df[df["calories_per_100g"].notna()].copy()

    # Remove obvious invalid values
    df = df[df["calories_per_100g"] >= 0].copy()

    # Drop duplicates by food_key, keeping the first valid row
    df = df.sort_values(
        by=["food_item", "calories_per_100g"],
        ascending=[True, True]
    ).drop_duplicates(subset=["food_key"], keep="first")

    # Reorder columns
    df = df[
        [
            "food_category",
            "food_item",
            "food_key",
            "serving_reference_g",
            "calories_per_100g",
            "kj_per_100g",
        ]
    ].reset_index(drop=True)

    return df


def main():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(RAW_PATH)
    cleaned_df = clean_calorie_dataset(raw_df)
    cleaned_df.to_csv(OUTPUT_PATH, index=False)

    print("✅ Cleaning completed.")
    print(f"Raw rows: {len(raw_df)}")
    print(f"Cleaned rows: {len(cleaned_df)}")
    print(f"Saved to: {OUTPUT_PATH}")
    print("\nPreview:")
    print(cleaned_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()