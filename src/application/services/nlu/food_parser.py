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
        "and",
        "add",
        "with",
        "plus",
        "please",
        "the",
        "a",
        "an",
        "my",
        "some",
        "have",
        "eat",
        "ate",
        "log",
        "track",
        "include",
        "including",
    }

    ITEM_PATTERN = re.compile(
        r"""
        (?P<food>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)*)
        \s+
        (?P<grams>\d+(?:\.\d+)?)g\b
        """,
        re.VERBOSE,
    )

    FOOD_ONLY_PATTERN = re.compile(
        r"""
        ^\s*
        [a-z][a-z\-]*(?:\s+[a-z][a-z\-]*)*
        \s*$
        """,
        re.VERBOSE,
    )

    QUANTITY_ONLY_PATTERN = re.compile(
        r"""
        ^\s*
        \d+(?:\.\d+)?\s*(?:g|gr|gram|grams)?
        \s*$
        """,
        re.VERBOSE,
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
        r"\bwhat is the total now\b",
        r"\bwhat's the total now\b",
        r"\bwhats the total now\b",
        r"\bwhat is the total\b",
        r"\bwhat's the total\b",
        r"\bwhats the total\b",
        r"\btotal now\b",
        r"\bcurrent total\b",
        r"\bmeal total\b",
        r"\bshow me the total\b",
    ]

    def parse_food_items(self, text: str) -> List[ParsedFoodItem]:
        text = self._prepare_text(text)

        if not text:
            return []

        matches = list(self.ITEM_PATTERN.finditer(text))
        items: List[ParsedFoodItem] = []

        last_end = -1
        for match in matches:
            if match.start() < last_end:
                continue

            raw_text = match.group(0).strip()
            original_food = match.group("food")
            food_name = self._clean_food_name(original_food)
            grams = float(match.group("grams"))

            if not food_name:
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
            last_end = match.end()

        return self._deduplicate_items(items)

    def extract_unparsed_text(self, text: str, items: List[ParsedFoodItem]) -> str:
        text = self._prepare_text(text)

        if not text:
            return ""

        if not items:
            return self._clean_leftover_text(text)

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
        return self._clean_leftover_text(leftover_text)

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
        if self.looks_like_quantity_only(text):
            return False
        if self._looks_like_command(text):
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

    def _prepare_text(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_food_name(self, food_name: str) -> str:
        food_name = self._prepare_text(food_name)

        words = food_name.split()
        while words and words[0] in self.LEADING_FILLERS:
            words.pop(0)

        while words and words[-1] in self.CONNECTORS:
            words.pop()

        cleaned = " ".join(words).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _clean_leftover_text(self, text: str) -> str:
        text = self._prepare_text(text)

        if not text:
            return ""

        # remove isolated connectors/fillers left behind by parsing
        words = [
            word
            for word in text.split()
            if word not in self.LEADING_FILLERS
        ]

        cleaned = " ".join(words).strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _deduplicate_items(self, items: List[ParsedFoodItem]) -> List[ParsedFoodItem]:
        unique: List[ParsedFoodItem] = []
        seen = set()

        for item in items:
            key = (
                item.food_name.strip().lower(),
                round(float(item.grams), 4),
                item.start,
                item.end,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique

    def _looks_like_command(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in self.COMMAND_PATTERNS)