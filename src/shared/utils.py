import re
from typing import List, Set


GENERIC_FOOD_TOKENS = {
    "food", "foods", "dish", "meal",
    "raw", "cooked", "fresh", "dried",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def split_meal_items(text: str) -> List[str]:
    normalized = normalize_text(text)
    parts = re.split(r"\s*(?:,| and | & |\+)\s*", normalized)
    return [p.strip() for p in parts if p.strip()]


def normalize_food_key(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def food_tokens(text: str) -> List[str]:
    normalized = normalize_food_key(text)
    if not normalized:
        return []
    return [tok for tok in normalized.split() if tok]


def meaningful_food_tokens(text: str) -> Set[str]:
    tokens = food_tokens(text)
    return {
        t for t in tokens
        if len(t) >= 4 and t not in GENERIC_FOOD_TOKENS
    }