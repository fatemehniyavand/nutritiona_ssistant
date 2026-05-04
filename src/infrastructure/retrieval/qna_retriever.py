from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.infrastructure.config.settings import settings
from src.infrastructure.retrieval.chroma_client import ChromaClientFactory


@dataclass
class QnARetrievalResult:
    document_id: str
    question: str
    answer: str
    document: str
    distance: float
    similarity: float
    metadata: dict[str, Any]


class QnARetriever:
    def __init__(self):
        self.collection = ChromaClientFactory.get_or_create_collection(
            settings.qna_collection
        )

    def search(self, query: str, n_results: int | None = None) -> list[QnARetrievalResult]:
        clean_query = self._normalize_query(query)

        if not clean_query:
            return []

        raw = self.collection.query(
            query_texts=[clean_query],
            n_results=n_results or settings.top_k_qna,
            include=["documents", "metadatas", "distances"],
        )

        ids = raw.get("ids", [[]])[0] or []
        documents = raw.get("documents", [[]])[0] or []
        metadatas = raw.get("metadatas", [[]])[0] or []
        distances = raw.get("distances", [[]])[0] or []

        results: list[QnARetrievalResult] = []

        for idx, document in enumerate(documents):
            doc_id = ids[idx] if idx < len(ids) else f"qna_doc_{idx + 1}"
            metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
            distance = float(distances[idx]) if idx < len(distances) else 999.0
            question, answer = self._split_question_answer(document)

            similarity = self._distance_to_similarity(distance)

            results.append(
                QnARetrievalResult(
                    document_id=str(doc_id),
                    question=question,
                    answer=answer,
                    document=document,
                    distance=distance,
                    similarity=similarity,
                    metadata=metadata,
                )
            )

        return results

    def _split_question_answer(self, document: str) -> tuple[str, str]:
        text = (document or "").strip()

        question_match = re.search(
            r"Question:\s*(.*?)\s*Answer:",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        answer_match = re.search(
            r"Answer:\s*(.*)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        question = question_match.group(1).strip() if question_match else ""
        answer = answer_match.group(1).strip() if answer_match else text

        return question, answer

    def _distance_to_similarity(self, distance: float) -> float:
        if distance < 0:
            return 0.0

        similarity = 1.0 / (1.0 + distance)
        return round(similarity, 4)

    def _normalize_query(self, query: str) -> str:
        text = (query or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text