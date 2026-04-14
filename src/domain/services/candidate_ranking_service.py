from typing import List, Dict, Any

from src.shared.utils import normalize_food_key, food_tokens


class CandidateRankingService:
    def rank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        query_key = normalize_food_key(query)
        query_tokens = set(food_tokens(query))

        ranked = []
        for candidate in candidates:
            food_item = candidate.get("food_item", "")
            candidate_key = normalize_food_key(food_item)
            candidate_tokens = set(food_tokens(food_item))

            lexical_score = candidate.get("lexical_score", 0.0)
            semantic_distance = candidate.get("semantic_distance")
            semantic_score = self._semantic_score(semantic_distance)

            exact_bonus = 0.0
            if query_key and candidate_key and query_key == candidate_key:
                exact_bonus = 1.0

            overlap_bonus = 0.0
            overlap = query_tokens.intersection(candidate_tokens)
            if len(overlap) >= 2:
                overlap_bonus = 0.35
            elif len(overlap) == 1 and len(query_tokens) == 1 and len(candidate_tokens) == 1:
                overlap_bonus = 0.25

            final_score = (
                exact_bonus * 1.5
                + lexical_score * 1.2
                + semantic_score * 0.4
                + overlap_bonus
            )

            enriched = dict(candidate)
            enriched["final_score"] = round(final_score, 4)
            ranked.append(enriched)

        ranked.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked

    def _semantic_score(self, distance: float | None) -> float:
        if distance is None:
            return 0.0

        if distance <= 0:
            return 1.0

        return 1.0 / (1.0 + distance)