from tqdm import tqdm

from src.infrastructure.config.settings import settings
from src.infrastructure.repositories.food_csv_repository import FoodCSVRepository
from src.infrastructure.retrieval.chroma_client import ChromaClientFactory


def main():
    repo = FoodCSVRepository(settings.calorie_csv_path)
    rows = repo.get_all()

    collection = ChromaClientFactory.get_or_create_collection(
        settings.calorie_collection
    )

    existing_count = collection.count()
    if existing_count > 0:
        print(f"Collection '{settings.calorie_collection}' already has {existing_count} documents.")
        print("If you want a fresh rebuild, delete storage/chroma first.")
        return

    documents = []
    metadatas = []
    ids = []

    for idx, row in enumerate(tqdm(rows, desc="Building calorie index")):
        food_item = row.get("food_item")
        food_key = row.get("food_key")
        food_category = row.get("food_category")
        serving_reference_g = row.get("serving_reference_g")
        calories_per_100g = row.get("calories_per_100g")
        kj_per_100g = row.get("kj_per_100g")

        if not food_item or calories_per_100g is None:
            continue

        document = (
            f"Food: {food_item}\n"
            f"Category: {food_category}\n"
            f"Serving reference: {serving_reference_g} g\n"
            f"Calories: {calories_per_100g} kcal per 100g\n"
            f"Energy: {kj_per_100g} kJ per 100g"
        )

        metadata = {
            "food_item": food_item,
            "food_key": food_key,
            "food_category": food_category,
            "serving_reference_g": float(serving_reference_g) if serving_reference_g is not None else 100.0,
            "calories_per_100g": float(calories_per_100g),
            "kj_per_100g": float(kj_per_100g) if kj_per_100g is not None else None,
        }

        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"food_{idx}")

    if not documents:
        print("No valid documents prepared for indexing.")
        return

    batch_size = 200
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )

    print(f"Done. Inserted {len(documents)} documents into '{settings.calorie_collection}'.")


if __name__ == "__main__":
    main()