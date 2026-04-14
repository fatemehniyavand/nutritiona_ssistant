from typing import List, Dict, Any

from src.shared.utils import food_tokens, normalize_food_key


AMBIGUOUS_SINGLE_WORDS = {
    "rice",
    "bread",
    "milk",
    "pizza",
    "cheese",
    "pasta",
    "juice",
}


class AmbiguityDetectionService:
    def is_ambiguous(self, query: str, ranked_candidates: List[Dict[str, Any]]) -> bool:
        tokens = food_tokens(query)
        normalized = normalize_food_key(query)

        if not tokens:
            return False

        # فقط بعضی queryهای تک‌کلمه‌ای واقعاً ambiguous حساب می‌شوند
        if len(tokens) == 1 and normalized in AMBIGUOUS_SINGLE_WORDS:
            exact_exists = any(
                normalize_food_key(c.get("food_item", "")) == normalized
                for c in ranked_candidates
            )
            return not exact_exists

        return False