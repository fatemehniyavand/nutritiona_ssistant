import chromadb


def main():
    candidate_dirs = [
        "storage/chroma",
        "chroma",
        "../chroma",
    ]

    client = None
    used_dir = None

    for directory in candidate_dirs:
        try:
            client = chromadb.PersistentClient(path=directory)
            used_dir = directory
            break
        except Exception:
            continue

    if client is None:
        print("❌ Could not open any Chroma directory.")
        print("Tried: storage/chroma, chroma, ../chroma")
        return

    print(f"✅ Using Chroma directory: {used_dir}")

    try:
        collection = client.get_collection("nutrition_db")
    except Exception as e:
        print(f"❌ Could not open collection 'nutrition_db': {e}")
        return

    count = collection.count()
    print("=" * 60)
    print(f"nutrition_db count: {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()