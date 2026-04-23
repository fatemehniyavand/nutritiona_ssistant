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
        r"\bremove\s+[a-z][a-z\s\-]*\b",
        r"\bdelete\s+[a-z][a-z\s\-]*\b",
        r"\btake out\s+[a-z][a-z\s\-]*\b",
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
        r"\b(what|which|why|how|is|are|can|should|do|does|healthy|protein|fat|vitamin|calories)\b",
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
        \b(gram|grams)\b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    GRAM_TOKEN_PATTERN = re.compile(r"\b\d+(?:\.\d+)?g\b", re.IGNORECASE)

    HARMLESS_LEFTOVER_WORDS = {
        "please",
        "and",
        "add",
        "with",
        "plus",
        "the",
        "a",
        "an",
        "my",
        "some",
        "track",
        "log",
        "include",
        "including",
    }

    def __init__(self):
        self.food_normalizer = FoodNormalizer()
        self.food_parser = FoodParser()
        self.intent_classifier = IntentClassifier()

    def parse(self, text: str) -> NLUResult:
        original_text = text or ""
        normalized_text = self.food_normalizer.normalize(original_text)

        if not original_text.strip():
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="empty",
                confidence="LOW",
                warnings=["User input is empty."],
            )

        forced_intent = self._override_command_intent(normalized_text)
        if forced_intent:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent=forced_intent,
                confidence="HIGH",
            )

        parsed_items = self.food_parser.parse_food_items(normalized_text)
        unparsed_text = self.food_parser.extract_unparsed_text(normalized_text, parsed_items)
        is_food_only = self.food_parser.looks_like_food_only(normalized_text)
        is_quantity_only = self.food_parser.looks_like_quantity_only(normalized_text)
        is_quantity_not_numeric = bool(self.NON_DIGIT_QUANTITY_PATTERN.search(original_text))

        warnings: List[str] = []

        # Highest-priority calorie routing:
        # if we successfully parsed food+grams, it is calorie input.
        if parsed_items:
            confidence = "HIGH"
            if unparsed_text and not self._is_harmless_leftover(unparsed_text):
                confidence = "MEDIUM"
                warnings.append(
                    f"Some text could not be confidently parsed: '{unparsed_text}'."
                )

            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=parsed_items,
                confidence=confidence,
                warnings=warnings,
                unparsed_text="" if self._is_harmless_leftover(unparsed_text) else unparsed_text,
                is_food_only=False,
                is_quantity_only=False,
                is_quantity_not_numeric=False,
            )

        # If grams/token patterns exist but no parsed items, this is still an attempted calorie input.
        if self.GRAM_TOKEN_PATTERN.search(normalized_text):
            if is_food_only:
                warnings.append("Food name detected, but quantity in grams is missing.")
            elif is_quantity_only:
                warnings.append("Quantity detected, but food name is missing.")
            else:
                warnings.append("Could not extract food and grams from calorie input.")

            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=[],
                confidence="LOW",
                warnings=warnings,
                unparsed_text=unparsed_text,
                is_food_only=is_food_only,
                is_quantity_only=is_quantity_only,
                is_quantity_not_numeric=False,
            )

        if is_quantity_not_numeric:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=[],
                confidence="LOW",
                warnings=["Quantity expression detected, but it is not written with digits."],
                unparsed_text=unparsed_text,
                is_food_only=False,
                is_quantity_only=False,
                is_quantity_not_numeric=True,
            )

        if is_food_only:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=[],
                confidence="LOW",
                warnings=["Food name detected, but quantity in grams is missing."],
                unparsed_text=unparsed_text,
                is_food_only=True,
                is_quantity_only=False,
                is_quantity_not_numeric=False,
            )

        if is_quantity_only:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="calorie_input",
                parsed_items=[],
                confidence="LOW",
                warnings=["Quantity detected, but food name is missing."],
                unparsed_text=unparsed_text,
                is_food_only=False,
                is_quantity_only=True,
                is_quantity_not_numeric=False,
            )

        classified_intent = self.intent_classifier.classify(normalized_text)

        if classified_intent == "nutrition_qa":
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="nutrition_qa",
                confidence="HIGH" if ("?" in original_text or self.QUESTION_HINT_PATTERN.search(normalized_text)) else "MEDIUM",
                warnings=[],
                unparsed_text="",
                is_food_only=False,
                is_quantity_only=False,
                is_quantity_not_numeric=False,
            )

        if classified_intent in {"clear_meal", "remove_item", "total_query"}:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent=classified_intent,
                confidence="HIGH",
                warnings=[],
                unparsed_text="",
                is_food_only=False,
                is_quantity_only=False,
                is_quantity_not_numeric=False,
            )

        if "?" in original_text or self.QUESTION_HINT_PATTERN.search(normalized_text):
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="nutrition_qa",
                confidence="MEDIUM",
                warnings=[],
                unparsed_text="",
                is_food_only=False,
                is_quantity_only=False,
                is_quantity_not_numeric=False,
            )

        return NLUResult(
            original_text=original_text,
            normalized_text=normalized_text,
            intent="unknown",
            confidence="LOW",
            warnings=["Intent could not be determined confidently."],
            unparsed_text=unparsed_text,
            is_food_only=False,
            is_quantity_only=False,
            is_quantity_not_numeric=False,
        )

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False

    def _override_command_intent(self, normalized_text: str) -> str:
        if self._matches_any(normalized_text, self.CLEAR_PATTERNS):
            return "clear_meal"

        if self._matches_any(normalized_text, self.REMOVE_PATTERNS):
            return "remove_item"

        if self._matches_any(normalized_text, self.TOTAL_PATTERNS):
            return "total_query"

        return ""

    def _is_harmless_leftover(self, text: str) -> bool:
        if not text:
            return True

        words = [w for w in text.split() if w.strip()]
        if not words:
            return True

        return all(word in self.HARMLESS_LEFTOVER_WORDS for word in words)