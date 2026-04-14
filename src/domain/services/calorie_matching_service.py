from typing import Dict, Any

from src.shared.constants import HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE
from src.shared.utils import normalize_food_key, food_tokens, meaningful_food_tokens


class CalorieMatchingService:
    def select_best_match(
        self,
        query: str,
        ranked_candidates: list[dict],
        is_ambiguous: bool,
    ) -> Dict[str, Any]:
        if not ranked_candidates:
            return {
                "accepted": False,
                "reason": "no_candidates",
                "confidence": LOW_CONFIDENCE,
                "candidate": None,
            }

        best = ranked_candidates[0]
        candidate_food = best.get("food_item", "")
        match_type = self.lexical_match_type(query, candidate_food)

        if is_ambiguous:
            return {
                "accepted": False,
                "reason": "ambiguous_query",
                "confidence": LOW_CONFIDENCE,
                "candidate": None,
            }

        if not match_type:
            return {
                "accepted": False,
                "reason": "no_reliable_match",
                "confidence": LOW_CONFIDENCE,
                "candidate": None,
            }

        confidence = self.confidence_from_lexical_match(match_type)

        return {
            "accepted": True,
            "reason": match_type,
            "confidence": confidence,
            "candidate": best,
        }

    def lexical_match_type(self, query: str, candidate: str) -> str | None:
        q = normalize_food_key(query)
        c = normalize_food_key(candidate)

        if not q or not c:
            return None

        if q == c:
            return "exact"

        q_tokens = food_tokens(q)
        c_tokens = food_tokens(c)

        if not q_tokens or not c_tokens:
            return None

        # single-word query: only exact single-word match is acceptable
        if len(q_tokens) == 1:
            if len(c_tokens) == 1 and q_tokens[0] == c_tokens[0]:
                return "exact"
            return None

        # multi-word exact prefix match
        if len(q_tokens) <= len(c_tokens) and c_tokens[:len(q_tokens)] == q_tokens:
            return "prefix"

        # multi-word strong overlap
        q_meaningful = meaningful_food_tokens(q)
        c_meaningful = meaningful_food_tokens(c)

        if not q_meaningful or not c_meaningful:
            return None

        overlap = q_meaningful.intersection(c_meaningful)
        if len(overlap) >= 2:
            return "strong_overlap"

        return None

    def confidence_from_lexical_match(self, match_type: str | None) -> str:
        if match_type == "exact":
            return HIGH_CONFIDENCE
        if match_type == "prefix":
            return HIGH_CONFIDENCE
        if match_type == "strong_overlap":
            return MEDIUM_CONFIDENCE
        return LOW_CONFIDENCE