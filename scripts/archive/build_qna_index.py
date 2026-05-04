from __future__ import annotations

from pathlib import Path

from tqdm import tqdm

from src.infrastructure.config.settings import settings
from src.infrastructure.retrieval.chroma_client import ChromaClientFactory


def load_qna_documents(path: str) -> list[str]:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Q&A file not found: {file_path}")

    text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        return []

    # هر بلاک جداشده با خط خالی = یک سند
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks


def main():
    documents = load_qna_documents(settings.qna_text_path)

    collection = ChromaClientFactory.get_or_create_collection(
        settings.qna_collection
    )

    existing_count = collection.count()
    if existing_count > 0:
        print(f"Collection '{settings.qna_collection}' already has {existing_count} documents.")
        print("If you want a fresh rebuild, delete storage/chroma first.")
        return

    if not documents:
        print("No Q&A documents found.")
        return

    ids = [f"qna_{i}" for i in range(len(documents))]
    metadatas = [{"source_type": "nutrition_qna"} for _ in documents]

    batch_size = 200
    for start in tqdm(range(0, len(documents), batch_size), desc="Building Q&A index"):
        end = start + batch_size
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )

    print(f"Done. Inserted {len(documents)} documents into '{settings.qna_collection}'.")


if __name__ == "__main__":
    main()