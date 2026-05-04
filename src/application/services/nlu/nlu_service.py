from dataclasses import dataclass, field
from typing import List
import re

from src.application.services.nlu.food_normalizer import FoodNormalizer
from src.application.services.nlu.food_parser import FoodParser, ParsedFoodItem
from src.application.services.nlu.intent_classifier import IntentClassifier


@dataclass
class NLUResult:
    original_text: str
    normalized_text: str
    intent: str
    parsed_items: List[ParsedFoodItem] = field(default_factory=list)
    confidence: str = "LOW"
    warnings: List[str] = field(default_factory=list)
    unparsed_text: str = ""
    is_food_only: bool = False
    is_quantity_only: bool = False
    is_quantity_not_numeric: bool = False


class NutritionNLUService:
    CLEAR_PATTERNS = [
        r"\bclear meal\b",
        r"\breset meal\b",
        r"\bempty meal\b",
        r"\bclear the meal\b",
        r"\bdelete meal\b",
    ]

    REMOVE_PATTERNS = [
        r"\bremove\s+[a-z][a-z\s'\-]*\b",
        r"\bdelete\s+[a-z][a-z\s'\-]*\b",
        r"\btake out\s+[a-z][a-z\s'\-]*\b",
    ]

    TOTAL_PATTERNS = [
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

    QUESTION_HINT_PATTERN = re.compile(
        r"\b(what|which|why|how|is|are|can|should|do|does|healthy|protein|fat|vitamin|fiber|diet|nutrition|nutritional|calories|carbs|sugar)\b",
        re.IGNORECASE,
    )

    NON_DIGIT_QUANTITY_PATTERN = re.compile(
        r"""
        \b(
            one|two|three|four|five|six|seven|eight|nine|ten|
            eleven|twelve|thirteen|fourteen|fifteen|sixteen|
            seventeen|eighteen|nineteen|twenty|thirty|forty|
            fifty|sixty|seventy|eighty|ninety|hundred|thousand
        )\b
        .*?
        \b(gram|grams|g)\b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    GRAM_TOKEN_PATTERN = re.compile(r"\b\d+(?:\.\d+)?g\b", re.IGNORECASE)

    HARMLESS_LEFTOVER_WORDS = {
        "please", "and", "add", "with", "plus",
        "the", "a", "an", "my", "some",
        "track", "log", "include", "including",
        "i", "want", "to", "eat", "ate", "have",
        "for", "meal", "today", "thanks", "thank", "you",
    }

    def __init__(self):
        self.food_normalizer = FoodNormalizer()
        self.food_parser = FoodParser()
        self.intent_classifier = IntentClassifier()

    def parse(self, text: str) -> NLUResult:
        original_text = text or ""
        normalized_text = self.food_normalizer.normalize(original_text)

        if not original_text.strip():
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="empty",
                confidence="LOW",
                warnings=["User input is empty."],
            )

        forced_intent = self._override_command_intent(normalized_text)
        if forced_intent:
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent=forced_intent,
                confidence="HIGH",
            )

        parsed_items = self.food_parser.parse_food_items(normalized_text)
        unparsed_text = self.food_parser.extract_unparsed_text(normalized_text, parsed_items)

        if parsed_items:
            clean_unparsed = "" if self._is_harmless_leftover(unparsed_text) else unparsed_text

            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=parsed_items,
                confidence="HIGH" if not clean_unparsed else "MEDIUM",
                warnings=[] if not clean_unparsed else [
                    f"Some text could not be confidently parsed: '{clean_unparsed}'."
                ],
                unparsed_text=clean_unparsed,
            )

        is_quantity_only = self.food_parser.looks_like_quantity_only(normalized_text)
        is_quantity_not_numeric = bool(self.NON_DIGIT_QUANTITY_PATTERN.search(original_text))

        if self.GRAM_TOKEN_PATTERN.search(normalized_text):
            warning = "Could not extract food and grams from calorie input."

            if is_quantity_only:
                warning = "Quantity detected, but food name is missing."

            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                confidence="LOW",
                warnings=[warning],
                unparsed_text=unparsed_text,
                is_quantity_only=is_quantity_only,
            )

        if is_quantity_not_numeric:
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                confidence="LOW",
                warnings=["Quantity expression detected, but it is not written with digits."],
                unparsed_text=unparsed_text,
                is_quantity_not_numeric=True,
            )

        classified_intent = self.intent_classifier.classify(normalized_text)

        if classified_intent in {"nutrition_qa", "clear_meal", "remove_item", "total_query"}:
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent=classified_intent,
                confidence="HIGH",
            )

        if "?" in original_text or self.QUESTION_HINT_PATTERN.search(normalized_text):
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="nutrition_qa",
                confidence="MEDIUM",
            )

        is_food_only = self.food_parser.looks_like_food_only(normalized_text)

        if is_food_only:
            return self._result(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                confidence="LOW",
                warnings=["Food name detected, but quantity in grams is missing."],
                unparsed_text=unparsed_text,
                is_food_only=True,
            )

        return self._result(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="unknown",
            confidence="LOW",
            warnings=["Intent could not be determined confidently."],
            unparsed_text=unparsed_text,
        )

    def _result(
        self,
        original_text: str,
        normalized_text: str,
        intent: str,
        parsed_items: List[ParsedFoodItem] = None,
        confidence: str = "LOW",
        warnings: List[str] = None,
        unparsed_text: str = "",
        is_food_only: bool = False,
        is_quantity_only: bool = False,
        is_quantity_not_numeric: bool = False,
    ) -> NLUResult:
        return NLUResult(
            original_text=original_text,
            normalized_text=normalized_text,
            intent=intent,
            parsed_items=parsed_items or [],
            confidence=confidence,
            warnings=warnings or [],
            unparsed_text=unparsed_text,
            is_food_only=is_food_only,
            is_quantity_only=is_quantity_only,
            is_quantity_not_numeric=is_quantity_not_numeric,
        )

    def _override_command_intent(self, normalized_text: str) -> str:
        if self._matches_any(normalized_text, self.CLEAR_PATTERNS):
            return "clear_meal"

        if self._matches_any(normalized_text, self.REMOVE_PATTERNS):
            return "remove_item"

        if self._matches_any(normalized_text, self.TOTAL_PATTERNS):
            return "total_query"

        return ""

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _is_harmless_leftover(self, text: str) -> bool:
        if not text:
            return True

        words = [word for word in text.split() if word.strip()]
        return all(word in self.HARMLESS_LEFTOVER_WORDS for word in words)
