import re


class FoodNormalizer:
    CONNECTORS = ("and", "add", "with", "plus")
    _CONNECTOR_PATTERN = "|".join(CONNECTORS)

    def normalize(self, text: str) -> str:
        text = self._basic_cleanup(text)

        if not text:
            return ""

        text = self._normalize_separators(text)
        text = self._fix_compact_gram_boundaries(text)
        text = self._separate_letters_and_digits(text)
        text = self._normalize_gram_expressions(text)
        text = self._fix_split_gram_followed_by_food(text)
        text = self._recover_glued_connectors(text)
        text = self._recover_glued_connector_prefixes(text)
        text = self._recover_compound_food_spacing(text)
        text = self._normalize_spaces(text)

        return text

    def _basic_cleanup(self, text: str) -> str:
        return (text or "").strip().lower()

    def _normalize_separators(self, text: str) -> str:
        text = re.sub(r"[,;|/]+", " ", text)
        text = re.sub(r"[^a-z0-9\s\.\-\?]", " ", text)
        text = re.sub(r"\s*-\s*", "-", text)
        return text

    def _fix_compact_gram_boundaries(self, text: str) -> str:
        # apple200grice150g -> apple200g rice150g
        text = re.sub(r"(\d+(?:\.\d+)?)g(?=[a-z])", r"\1g ", text)
        return text

    def _separate_letters_and_digits(self, text: str) -> str:
        text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
        text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
        return text

    def _normalize_gram_expressions(self, text: str) -> str:
        text = re.sub(r"(\d+(?:\.\d+)?)\s*(g|gram|grams)\b", r"\1g", text)
        return text

    def _fix_split_gram_followed_by_food(self, text: str) -> str:
        # "200 g rice" -> "200g rice"
        text = re.sub(r"(\d+(?:\.\d+)?)\s+g\s+(?=[a-z])", r"\1g ", text)
        # "200 g" at end
        text = re.sub(r"(\d+(?:\.\d+)?)\s+g\b", r"\1g", text)
        return text

    def _recover_glued_connectors(self, text: str) -> str:
        text = re.sub(
            rf"(\d+(?:\.\d+)?g)((?:{self._CONNECTOR_PATTERN}))\b",
            r"\1 \2",
            text,
        )

        text = re.sub(
            rf"([a-z\-])((?:{self._CONNECTOR_PATTERN}))([a-z])",
            r"\1 \2 \3",
            text,
        )

        return text

    def _recover_glued_connector_prefixes(self, text: str) -> str:
        text = re.sub(
            rf"\b((?:{self._CONNECTOR_PATTERN}))([a-z])",
            r"\1 \2",
            text,
        )
        return text

    def _recover_compound_food_spacing(self, text: str) -> str:
        text = re.sub(r"(\d+(?:\.\d+)?g)([a-z])", r"\1 \2", text)
        text = re.sub(r"\s*-\s*", "-", text)
        return text

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()