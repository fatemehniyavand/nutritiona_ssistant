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
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand)\b.*\b(gram|grams)\b",
        re.IGNORECASE,
    )

    def __init__(self):
        self.food_normalizer = FoodNormalizer()
        self.food_parser = FoodParser()
        self.intent_classifier = IntentClassifier()

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

    def parse(self, text: str) -> NLUResult:
        original_text = text or ""
        normalized_text = self.food_normalizer.normalize(original_text)

        parsed_items: List[ParsedFoodItem] = []
        warnings: List[str] = []
        confidence = "LOW"
        unparsed_text = ""
        is_food_only = False
        is_quantity_only = False

        if not original_text.strip():
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent="empty",
                parsed_items=[],
                confidence="LOW",
                warnings=["User input is empty."],
                unparsed_text="",
                is_food_only=False,
                is_quantity_only=False,
            )

        forced_intent = self._override_command_intent(normalized_text)
        if forced_intent:
            return NLUResult(
                original_text=original_text,
                normalized_text=normalized_text,
                intent=forced_intent,
                parsed_items=[],
                confidence="HIGH",
                warnings=[],
                unparsed_text="",
                is_food_only=False,
                is_quantity_only=False,
            )

        parsed_items = self.food_parser.parse_food_items(normalized_text)
        unparsed_text = self.food_parser.extract_unparsed_text(normalized_text, parsed_items)
        is_food_only = self.food_parser.looks_like_food_only(normalized_text)
        is_quantity_only = self.food_parser.looks_like_quantity_only(normalized_text)

        intent = self.intent_classifier.classify(normalized_text)

        if intent == "empty":
            warnings.append("User input is empty.")
            confidence = "LOW"

        elif intent == "calorie_input":
            if parsed_items:
                if not unparsed_text:
                    confidence = "HIGH"
                else:
                    confidence = "MEDIUM"
                    warnings.append(
                        f"Some text could not be confidently parsed: '{unparsed_text}'."
                    )

            else:
                if is_food_only:
                    warnings.append("Food name detected, but quantity in grams is missing.")
                elif is_quantity_only:
                    warnings.append("Quantity detected, but food name is missing.")
                elif self.NON_DIGIT_QUANTITY_PATTERN.search(original_text):
                    warnings.append("Quantity expression detected, but it is not written with digits.")
                else:
                    warnings.append("Could not extract food and grams from calorie input.")

                confidence = "LOW"

        elif intent in {"clear_meal", "remove_item", "total_query"}:
            confidence = "HIGH"

        elif intent == "nutrition_qa":
            confidence = "HIGH"

            if parsed_items:
                intent = "calorie_input"
                if not unparsed_text:
                    confidence = "HIGH"
                else:
                    confidence = "MEDIUM"
                    warnings.append(
                        f"Some text could not be confidently parsed: '{unparsed_text}'."
                    )

            elif is_food_only:
                warnings.append("Food name detected, but quantity in grams is missing.")
                confidence = "LOW"

            elif is_quantity_only:
                warnings.append("Quantity detected, but food name is missing.")
                confidence = "LOW"

            elif unparsed_text and not self.QUESTION_HINT_PATTERN.search(normalized_text):
                warnings.append(
                    f"Unparsed text remained after lightweight inspection: '{unparsed_text}'."
                )
                confidence = "MEDIUM"

        else:
            if parsed_items:
                intent = "calorie_input"
                if not unparsed_text:
                    confidence = "HIGH"
                else:
                    confidence = "MEDIUM"
                    warnings.append(
                        f"Some text could not be confidently parsed: '{unparsed_text}'."
                    )

            elif is_food_only:
                warnings.append("Food name detected, but quantity in grams is missing.")
                confidence = "LOW"

            elif is_quantity_only:
                warnings.append("Quantity detected, but food name is missing.")
                confidence = "LOW"

            elif self.NON_DIGIT_QUANTITY_PATTERN.search(original_text):
                warnings.append("Quantity expression detected, but it is not written with digits.")
                confidence = "LOW"

            else:
                if "?" in original_text or self.QUESTION_HINT_PATTERN.search(normalized_text):
                    intent = "nutrition_qa"
                    confidence = "MEDIUM"
                else:
                    warnings.append("Intent could not be determined confidently.")
                    confidence = "LOW"

        return NLUResult(
            original_text=original_text,
            normalized_text=normalized_text,
            intent=intent,
            parsed_items=parsed_items,
            confidence=confidence,
            warnings=warnings,
            unparsed_text=unparsed_text,
            is_food_only=is_food_only,
            is_quantity_only=is_quantity_only,
        )