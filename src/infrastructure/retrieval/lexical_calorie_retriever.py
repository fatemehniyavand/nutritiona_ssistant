from typing import List, Dict, Any

from src.infrastructure.config.settings import settings
from src.infrastructure.repositories.food_csv_repository import FoodCSVRepository
from src.shared.utils import normalize_food_key, food_tokens


class LexicalCalorieRetriever:
    _rows: list[dict] | None = None

    def __init__(self):
        if self.__class__._rows is None:
            repo = FoodCSVRepository(settings.calorie_csv_path)
            self.__class__._rows = repo.get_all()

        self.rows = self.__class__._rows or []

    def search(self, query: str, limit: int | None = None) -> List[Dict[str, Any]]:
        limit = limit or settings.top_k_calorie
        query_key = normalize_food_key(query)
        query_tokens = set(food_tokens(query))

        scored = []

        for row in self.rows:
            candidate_food = str(row.get("food_item", "")).strip()
            candidate_key = normalize_food_key(candidate_food)
            candidate_tokens = set(food_tokens(candidate_food))

            lexical_score = self._score_candidate(
                query_key=query_key,
                query_tokens=query_tokens,
                candidate_key=candidate_key,
                candidate_tokens=candidate_tokens,
            )

            if lexical_score <= 0:
                continue

            scored.append(
                {
                    "source": "lexical",
                    "food_item": row.get("food_item"),
                    "food_key": row.get("food_key"),
                    "food_category": row.get("food_category"),
                    "serving_reference_g": row.get("serving_reference_g"),
                    "calories_per_100g": row.get("calories_per_100g"),
                    "kj_per_100g": row.get("kj_per_100g"),
                    "lexical_score": lexical_score,
                    "semantic_distance": None,
                }
            )

        scored.sort(key=lambda x: x["lexical_score"], reverse=True)
        return scored[:limit]

    def _score_candidate(
        self,
        query_key: str,
        query_tokens: set[str],
        candidate_key: str,
        candidate_tokens: set[str],
    ) -> float:
        if not query_key or not candidate_key:
            return 0.0

        if query_key == candidate_key:
            return 1.0

        if len(query_tokens) == 1 and len(candidate_tokens) == 1:
            if query_tokens == candidate_tokens:
                return 0.98

        if len(query_tokens) > 1:
            candidate_token_list = list(candidate_tokens)
            if query_tokens.issubset(candidate_tokens):
                return 0.9

        overlap = query_tokens.intersection(candidate_tokens)
        if len(query_tokens) > 1 and len(overlap) >= 2:
            return 0.75

        return 0.0