import re


class FoodNormalizer:
    CONNECTORS = ("and", "add", "with", "plus")
    _CONNECTOR_PATTERN = "|".join(CONNECTORS)
    DECIMAL_MARKER = "§"

    def normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = text.replace("’", "'").replace("`", "'")

        if not text:
            return ""

        text = self._protect_decimal_points(text)
        text = self._normalize_symbols(text)
        text = self._recover_glued_gram_units(text)
        text = self._insert_letter_number_spaces(text)
        text = self._normalize_gram_units(text)
        text = self._recover_glued_connectors(text)
        text = self._recover_adjacent_items(text)
        text = self._restore_decimal_points(text)
        text = self._normalize_spaces(text)

        return text

    def _protect_decimal_points(self, text: str) -> str:
        return re.sub(r"(\d)\.(\d)", rf"\1{self.DECIMAL_MARKER}\2", text)

    def _restore_decimal_points(self, text: str) -> str:
        return text.replace(self.DECIMAL_MARKER, ".")

    def _normalize_symbols(self, text: str) -> str:
        text = text.replace("&", " and ")
        text = text.replace("+", " plus ")
        text = re.sub(r"[,;|/]+", " ", text)
        text = re.sub(r"[^a-z0-9§\s\-']", " ", text)
        text = re.sub(r"-{2,}", " ", text)
        text = re.sub(r"\s*-\s*", "-", text)
        return text

    def _recover_glued_gram_units(self, text: str) -> str:
        return re.sub(
            rf"(\d+(?:{re.escape(self.DECIMAL_MARKER)}\d+)?)(g|gr|gram|grams)(?=[a-z])",
            r"\1\2 ",
            text,
        )

    def _insert_letter_number_spaces(self, text: str) -> str:
        text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
        text = re.sub(rf"(\d)(?!{re.escape(self.DECIMAL_MARKER)})([a-z])", r"\1 \2", text)
        return text

    def _normalize_gram_units(self, text: str) -> str:
        return re.sub(
            rf"\b(\d+(?:{re.escape(self.DECIMAL_MARKER)}\d+)?)\s*(?:g|gr|gram|grams)\b",
            r"\1g",
            text,
        )

    def _recover_glued_connectors(self, text: str) -> str:
        text = re.sub(
            rf"\b({self._CONNECTOR_PATTERN})(?=[a-z])",
            r"\1 ",
            text,
        )
        text = re.sub(
            rf"(\d+(?:{re.escape(self.DECIMAL_MARKER)}\d+)?g)({self._CONNECTOR_PATTERN})\b",
            r"\1 \2",
            text,
        )
        text = re.sub(
            rf"(\d+(?:{re.escape(self.DECIMAL_MARKER)}\d+)?g)\s*({self._CONNECTOR_PATTERN})(?=[a-z])",
            r"\1 \2 ",
            text,
        )
        return text

    def _recover_adjacent_items(self, text: str) -> str:
        return re.sub(
            rf"(\d+(?:{re.escape(self.DECIMAL_MARKER)}\d+)?g)(?=[a-z])",
            r"\1 ",
            text,
        )

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
