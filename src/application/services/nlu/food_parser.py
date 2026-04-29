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
    CONNECTORS = {"and", "add", "with", "plus"}

    LEADING_FILLERS = {
        "and", "add", "with", "plus",
        "please", "the", "a", "an", "my", "some",
        "have", "eat", "ate", "eaten",
        "log", "track", "include", "including",
        "i", "want", "to", "for", "meal", "hello", "hi", "hey",
    }

    ITEM_PATTERN = re.compile(
        r"""
        (?P<food>
            [a-z][a-z'\-]*
            (?:
                \s+
                (?!(?:and|add|with|plus)\b)
                [a-z][a-z'\-]*
            )*
        )
        \s+
        (?P<grams>\d+(?:\.\d+)?)g\b
        """,
        re.VERBOSE,
    )

    FOOD_ONLY_PATTERN = re.compile(
        r"^[a-z][a-z'\-]*(?:\s+[a-z][a-z'\-]*)*$"
    )

    QUANTITY_ONLY_PATTERN = re.compile(
        r"^\d+(?:\.\d+)?\s*(?:g|gr|gram|grams)?$"
    )

    COMMAND_PATTERNS = [
        r"\bclear meal\b",
        r"\breset meal\b",
        r"\bdelete meal\b",
        r"\bempty meal\b",
        r"\bclear the meal\b",
        r"\bremove\s+[a-z]",
        r"\bdelete\s+[a-z]",
        r"\btake out\s+[a-z]",
        r"\bwhat is the total\b",
        r"\bwhat's the total\b",
        r"\bwhats the total\b",
        r"\btotal now\b",
        r"\bcurrent total\b",
        r"\bmeal total\b",
    ]

    def parse(self, text: str) -> List[ParsedFoodItem]:
        return self.parse_food_items(text)

    def parse_food_items(self, text: str) -> List[ParsedFoodItem]:
        text = self._prepare_text(text)
        if not text:
            return []

        protected_text = self._protect_item_boundaries(text)
        items: List[ParsedFoodItem] = []

        for match in self.ITEM_PATTERN.finditer(protected_text):
            raw_text = match.group(0).strip()
            food_name = self._clean_food_name(match.group("food"))
            grams = float(match.group("grams"))

            if not food_name:
                continue

            if grams <= 0:
                continue

            if self._looks_like_command(food_name):
                continue

            items.append(
                ParsedFoodItem(
                    raw_text=raw_text,
                    food_name=food_name,
                    grams=grams,
                    start=match.start(),
                    end=match.end(),
                )
            )

        return self._deduplicate_items(items)

    def parse_single_food_item(self, text: str) -> Optional[ParsedFoodItem]:
        items = self.parse_food_items(text)
        return items[0] if len(items) == 1 else None

    def extract_unparsed_text(self, text: str, items: List[ParsedFoodItem]) -> str:
        text = self._prepare_text(text)
        if not text:
            return ""

        if not items:
            return self._clean_leftover_text(text)

        protected_text = self._protect_item_boundaries(text)
        spans = sorted((item.start, item.end) for item in items)

        leftovers: List[str] = []
        current = 0

        for start, end in spans:
            if start > current:
                leftovers.append(protected_text[current:start])
            current = max(current, end)

        if current < len(protected_text):
            leftovers.append(protected_text[current:])

        return self._clean_leftover_text(" ".join(leftovers))

    def looks_like_food_only(self, text: str) -> bool:
        text = self._prepare_text(text)

        if not text:
            return False
        if self.parse_food_items(text):
            return False
        if self.looks_like_quantity_only(text):
            return False
        if self._looks_like_command(text):
            return False
        if "?" in text:
            return False
        if re.search(r"\d", text):
            return False

        cleaned = self._clean_food_name(text)
        if not cleaned:
            return False

        return self.FOOD_ONLY_PATTERN.match(cleaned) is not None

    def looks_like_quantity_only(self, text: str) -> bool:
        text = self._prepare_text(text)

        if not text:
            return False
        if self.parse_food_items(text):
            return False
        if self._looks_like_command(text):
            return False

        return self.QUANTITY_ONLY_PATTERN.match(text) is not None

    def _protect_item_boundaries(self, text: str) -> str:
        text = re.sub(r"(\d+(?:\.\d+)?g)\s+(?=[a-z])", r"\1 | ", text)
        text = text.replace(" | and ", " and ")
        text = text.replace(" | add ", " add ")
        text = text.replace(" | with ", " with ")
        text = text.replace(" | plus ", " plus ")
        return text

    def _prepare_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower()).strip()

    def _clean_food_name(self, food_name: str) -> str:
        food_name = food_name.replace("|", " ")
        words = self._prepare_text(food_name).split()

        while words and words[0] in self.LEADING_FILLERS:
            words.pop(0)

        while words and words[-1] in self.CONNECTORS:
            words.pop()

        return " ".join(words).strip()

    def _clean_leftover_text(self, text: str) -> str:
        text = text.replace("|", " ")
        words = self._prepare_text(text).split()
        words = [word for word in words if word not in self.LEADING_FILLERS]
        words = [word for word in words if word not in self.CONNECTORS]
        return " ".join(words).strip()

    def _deduplicate_items(self, items: List[ParsedFoodItem]) -> List[ParsedFoodItem]:
        unique: List[ParsedFoodItem] = []
        seen = set()

        for item in items:
            key = (item.food_name.lower(), round(float(item.grams), 4))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique

    def _looks_like_command(self, text: str) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in self.COMMAND_PATTERNS)
