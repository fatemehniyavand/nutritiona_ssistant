import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ParsedFoodItem:
    raw_text: str
    food_name: str
    grams: float
    start: int
    end: int


class FoodParser:
    CONNECTOR_PATTERN = r"(?:and|add|with|plus)"

    ITEM_PATTERN = re.compile(
        rf"""
        (?:
            ^\s*
            |
            \s*\b{CONNECTOR_PATTERN}\b\s+
            |
            \s+
        )
        (?P<food>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)*)
        \s+
        (?P<grams>\d+(?:\.\d+)?)g\b
        """,
        re.VERBOSE,
    )

    FOOD_ONLY_PATTERN = re.compile(
        rf"""
        ^\s*
        (?:{CONNECTOR_PATTERN}\s+)?
        (?P<food>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)*)
        \s*$
        """,
        re.VERBOSE,
    )

    QUANTITY_ONLY_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<grams>\d+(?:\.\d+)?)g
        \s*$
        """,
        re.VERBOSE,
    )

    def parse_food_items(self, text: str) -> List[ParsedFoodItem]:
        text = self._prepare_text(text)

        if not text:
            return []

        items: List[ParsedFoodItem] = []
        cursor = 0

        while cursor < len(text):
            match = self.ITEM_PATTERN.search(text, cursor)

            if not match:
                break

            raw_text = match.group(0).strip()
            food_name = self._clean_food_name(match.group("food"))
            grams = float(match.group("grams"))

            if food_name:
                items.append(
                    ParsedFoodItem(
                        raw_text=raw_text,
                        food_name=food_name,
                        grams=grams,
                        start=match.start(),
                        end=match.end(),
                    )
                )

            cursor = match.end()

        return self._deduplicate_items(items)

    def extract_unparsed_text(self, text: str, items: List[ParsedFoodItem]) -> str:
        text = self._prepare_text(text)

        if not text:
            return ""

        if not items:
            return self._strip_connectors(text)

        spans = sorted((item.start, item.end) for item in items)
        leftovers: List[str] = []
        current = 0

        for start, end in spans:
            if start > current:
                leftovers.append(text[current:start])
            current = max(current, end)

        if current < len(text):
            leftovers.append(text[current:])

        leftover_text = " ".join(leftovers)
        leftover_text = self._strip_connectors(leftover_text)
        leftover_text = re.sub(r"\s+", " ", leftover_text).strip()

        return leftover_text

    def parse_single_food_item(self, text: str) -> Optional[ParsedFoodItem]:
        items = self.parse_food_items(text)
        if len(items) == 1:
            return items[0]
        return None

    def looks_like_food_only(self, text: str) -> bool:
        text = self._prepare_text(text)

        if not text:
            return False
        if self.parse_food_items(text):
            return False
        if self.QUANTITY_ONLY_PATTERN.match(text):
            return False
        if self._looks_like_command(text):
            return False

        return self.FOOD_ONLY_PATTERN.match(text) is not None

    def looks_like_quantity_only(self, text: str) -> bool:
        text = self._prepare_text(text)

        if not text:
            return False
        if self.parse_food_items(text):
            return False
        if self._looks_like_command(text):
            return False

        return self.QUANTITY_ONLY_PATTERN.match(text) is not None

    def _prepare_text(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_food_name(self, food_name: str) -> str:
        food_name = re.sub(r"\s+", " ", food_name).strip()
        # remove accidental leading connector if captured by noisy input
        food_name = re.sub(rf"^(?:{self.CONNECTOR_PATTERN})\s+", "", food_name).strip()
        return food_name

    def _strip_connectors(self, text: str) -> str:
        text = re.sub(rf"\b{self.CONNECTOR_PATTERN}\b", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _deduplicate_items(self, items: List[ParsedFoodItem]) -> List[ParsedFoodItem]:
        unique: List[ParsedFoodItem] = []
        seen = set()

        for item in items:
            key = (item.start, item.end, item.food_name, item.grams)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique

    def _looks_like_command(self, text: str) -> bool:
        command_patterns = [
            r"\bclear meal\b",
            r"\breset meal\b",
            r"\bdelete meal\b",
            r"\bempty meal\b",
            r"\bclear the meal\b",
            r"\bremove\s+[a-z]",
            r"\bdelete\s+[a-z]",
            r"\btake out\s+[a-z]",
            r"\bwhat is the total now\b",
            r"\bwhat's the total now\b",
            r"\bwhats the total now\b",
            r"\btotal now\b",
            r"\bcurrent total\b",
            r"\bmeal total\b",
        ]
        return any(re.search(pattern, text) for pattern in command_patterns)