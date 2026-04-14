from typing import List, Dict, Any

from src.infrastructure.config.settings import settings
from src.infrastructure.retrieval.calorie_retriever import CalorieRetriever
from src.infrastructure.retrieval.lexical_calorie_retriever import LexicalCalorieRetriever


class HybridCalorieRetriever:
    def __init__(self):
        self.lexical_retriever = LexicalCalorieRetriever()
        self.semantic_retriever = CalorieRetriever()

    def search(self, query: str, limit: int | None = None) -> List[Dict[str, Any]]:
        limit = limit or settings.top_k_calorie

        lexical_candidates = self.lexical_retriever.search(query, limit=limit)

        semantic_result = self.semantic_retriever.search(query, n_results=limit)
        semantic_metadatas = semantic_result.get("metadatas", [[]])[0]
        semantic_distances = semantic_result.get("distances", [[]])[0]

        semantic_candidates = []
        for idx, meta in enumerate(semantic_metadatas):
            semantic_candidates.append(
                {
                    "source": "semantic",
                    "food_item": meta.get("food_item"),
                    "food_key": meta.get("food_key"),
                    "food_category": meta.get("food_category"),
                    "serving_reference_g": meta.get("serving_reference_g"),
                    "calories_per_100g": meta.get("calories_per_100g"),
                    "kj_per_100g": meta.get("kj_per_100g"),
                    "lexical_score": 0.0,
                    "semantic_distance": semantic_distances[idx] if idx < len(semantic_distances) else None,
                }
            )

        merged = {}
        for candidate in lexical_candidates + semantic_candidates:
            key = candidate.get("food_key") or candidate.get("food_item")
            if not key:
                continue

            if key not in merged:
                merged[key] = candidate
            else:
                merged[key]["lexical_score"] = max(
                    merged[key].get("lexical_score", 0.0),
                    candidate.get("lexical_score", 0.0),
                )

                old_distance = merged[key].get("semantic_distance")
                new_distance = candidate.get("semantic_distance")

                if old_distance is None:
                    merged[key]["semantic_distance"] = new_distance
                elif new_distance is not None:
                    merged[key]["semantic_distance"] = min(old_distance, new_distance)

        candidates = list(merged.values())
        return candidates[: max(limit * 2, 10)]