import csv
from pathlib import Path


CANDIDATE_PATHS = [
    "data/raw/calories.csv",
    "data/raw/food_calories.csv",
    "data/raw/Calories in Food Items per 100 grams.csv",
    "data/processed/calories.csv",
]


def find_existing_file():
    for path in CANDIDATE_PATHS:
        p = Path(path)
        if p.exists():
            return p
    return None


def main():
    file_path = find_existing_file()

    if file_path is None:
        print("❌ No known calorie CSV file was found.")
        print("Checked paths:")
        for p in CANDIDATE_PATHS:
            print(f" - {p}")
        return

    print(f"✅ Using file: {file_path}")

    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total_rows = len(rows)

    unique_foods = set()
    categories = set()

    possible_food_keys = ["FoodItem", "food_item", "food", "item", "name"]
    possible_category_keys = ["FoodCategory", "food_category", "category"]

    for row in rows:
        for key in possible_food_keys:
            if key in row and row[key]:
                unique_foods.add(row[key].strip().lower())
                break

        for key in possible_category_keys:
            if key in row and row[key]:
                categories.add(row[key].strip().lower())
                break

    print("=" * 60)
    print(f"Total CSV rows        : {total_rows}")
    print(f"Unique food names     : {len(unique_foods)}")
    print(f"Unique categories     : {len(categories)}")
    print("=" * 60)

    preview = sorted(list(unique_foods))[:30]
    print("Sample food items:")
    for item in preview:
        print(f" - {item}")


if __name__ == "__main__":
    main()