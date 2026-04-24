import re


class FoodNormalizer:
    CONNECTORS = ("and", "add", "with", "plus")
    _CONNECTOR_PATTERN = "|".join(CONNECTORS)

    def normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = text.replace("’", "'").replace("`", "'")

        if not text:
            return ""

        text = self._protect_decimal_points(text)
        text = self._normalize_symbols(text)

        # apple100gbanana200gmilk50g -> apple100g banana200g milk50g
        text = re.sub(
            r"(\d+(?:__DECIMAL__\d+)?)(?:g|gr|gram|grams)(?=[a-z])",
            r"\1g ",
            text,
        )

        # rice100gandmilk200g -> rice100g and milk200g
        text = re.sub(
            rf"(\d+(?:__DECIMAL__\d+)?g)\s*({self._CONNECTOR_PATTERN})(?=[a-z])",
            r"\1 \2 ",
            text,
        )

        text = self._recover_glued_prefix_connectors(text)
        text = self._insert_letter_number_spaces(text)
        text = self._normalize_gram_units(text)
        text = self._recover_glued_after_grams(text)
        text = self._restore_decimal_points(text)
        text = self._normalize_spaces(text)

        return text

    def _protect_decimal_points(self, text: str) -> str:
        return re.sub(r"(\d)\.(\d)", r"\1__DECIMAL__\2", text)

    def _restore_decimal_points(self, text: str) -> str:
        return text.replace("__DECIMAL__", ".")

    def _normalize_symbols(self, text: str) -> str:
        text = re.sub(r"[,;|/]+", " ", text)
        text = text.replace("&", " and ")
        text = text.replace("+", " plus ")
        text = re.sub(r"[^a-z0-9_\s\-']", " ", text)
        text = re.sub(r"\s*-\s*", "-", text)
        return text

    def _recover_glued_prefix_connectors(self, text: str) -> str:
        return re.sub(
            rf"\b({self._CONNECTOR_PATTERN})(?=[a-z])",
            r"\1 ",
            text,
        )

    def _insert_letter_number_spaces(self, text: str) -> str:
        text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
        text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
        return text

    def _normalize_gram_units(self, text: str) -> str:
        return re.sub(
            r"\b(\d+(?:__DECIMAL__\d+)?)\s*(?:g|gr|gram|grams)\b",
            r"\1g",
            text,
        )

    def _recover_glued_after_grams(self, text: str) -> str:
        text = re.sub(
            rf"(\d+(?:__DECIMAL__\d+)?g)({self._CONNECTOR_PATTERN})\b",
            r"\1 \2",
            text,
        )

        text = re.sub(
            r"(\d+(?:__DECIMAL__\d+)?g)(?=[a-z])",
            r"\1 ",
            text,
        )

        return text

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()