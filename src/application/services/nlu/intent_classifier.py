import re


class IntentClassifier:
    """
    Detects the user's intent for the nutrition assistant.
    Priority:
    1) empty
    2) clear / remove / total commands
    3) calorie-like meal input
    4) nutrition QA
    """

    def classify(self, text: str) -> str:
        text = (text or "").strip().lower()

        if not text:
            return "empty"

        if self._is_clear_meal(text):
            return "clear_meal"

        if self._is_remove_item(text):
            return "remove_item"

        if self._is_total_query(text):
            return "total_query"

        if self._looks_like_calorie_input(text):
            return "calorie_input"

        if self._looks_like_nutrition_question(text):
            return "nutrition_qa"

        return "unknown"

    def _is_clear_meal(self, text: str) -> bool:
        patterns = [
            r"\bclear meal\b",
            r"\breset meal\b",
            r"\bdelete meal\b",
            r"\bempty meal\b",
            r"\bclear the meal\b",
            r"\bstart over\b",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _is_remove_item(self, text: str) -> bool:
        patterns = [
            r"\bremove\s+[a-z]",
            r"\bdelete\s+[a-z]",
            r"\btake out\s+[a-z]",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _is_total_query(self, text: str) -> bool:
        patterns = [
            r"\bwhat is the total now\b",
            r"\bwhat's the total now\b",
            r"\bwhats the total now\b",
            r"\bwhat is the total\b",
            r"\bwhat's the total\b",
            r"\bwhats the total\b",
            r"\bcurrent total\b",
            r"\bmeal total\b",
            r"\btotal now\b",
            r"\bshow me the total\b",
            r"\bhow many calories(?: do i have)?\b",
            r"\bsum\b",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _looks_like_calorie_input(self, text: str) -> bool:
        if re.search(r"\d+(?:\.\d+)?g\b", text):
            return True

        if re.search(r"^(?:and|add|with|plus)\b", text) and re.search(r"\d", text):
            return True

        if re.search(r"\b(?:remove|delete|clear meal|reset meal)\b", text):
            return True

        return False

    def _looks_like_nutrition_question(self, text: str) -> bool:
        patterns = [
            r"^what\b",
            r"^is\b",
            r"^are\b",
            r"^why\b",
            r"^how\b",
            r"^can\b",
            r"^does\b",
            r"^do\b",
            r"\?$",
            r"\bhealthy\b",
            r"\bprotein\b",
            r"\bcarb\b",
            r"\bcarbs\b",
            r"\bfat\b",
            r"\bfats\b",
            r"\bvitamin\b",
            r"\bvitamins\b",
            r"\bnutrition\b",
            r"\bbenefit\b",
            r"\bbenefits\b",
            r"\bweight loss\b",
        ]
        return any(re.search(pattern, text) for pattern in patterns)