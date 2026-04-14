from src.infrastructure.config.settings import settings
from src.infrastructure.retrieval.chroma_client import ChromaClientFactory


class QnARetriever:
    def __init__(self):
        self.collection = ChromaClientFactory.get_or_create_collection(
            settings.qna_collection
        )

    def search(self, query: str, n_results: int | None = None):
        return self.collection.query(
            query_texts=[query],
            n_results=n_results or settings.top_k_qna,
            include=["documents", "metadatas", "distances"],
        )