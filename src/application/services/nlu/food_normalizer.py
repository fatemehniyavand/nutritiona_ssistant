import re


class FoodNormalizer:
    CONNECTORS = ("and", "add", "with", "plus")
    _CONNECTOR_PATTERN = "|".join(CONNECTORS)

    def normalize(self, text: str) -> str:
        text = self._basic_cleanup(text)

        if not text:
            return ""

        text = self._protect_decimal_points(text)
        text = self._normalize_separators(text)
        text = self._recover_glued_connector_prefixes(text)
        text = self._insert_space_between_food_and_number(text)
        text = self._normalize_gram_expressions(text)
        text = self._recover_glued_connectors_after_grams(text)
        text = self._fix_compact_gram_boundaries(text)
        text = self._restore_decimal_points(text)
        text = self._normalize_spaces(text)

        return text

    def _basic_cleanup(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = text.replace("’", "'").replace("`", "'")
        return text

    def _protect_decimal_points(self, text: str) -> str:
        return re.sub(r"(\d)\.(\d)", r"\1__DECIMAL__\2", text)

    def _restore_decimal_points(self, text: str) -> str:
        return text.replace("__DECIMAL__", ".")

    def _normalize_separators(self, text: str) -> str:
        text = re.sub(r"[,;|/]+", " ", text)
        text = re.sub(r"&", " and ", text)
        text = re.sub(r"\+", " plus ", text)

        # keep only letters, digits, spaces, hyphen, and protected decimal token
        text = re.sub(r"[^a-z0-9_\s\-]", " ", text)

        # collapse repeated hyphen spacing
        text = re.sub(r"\s*-\s*", "-", text)
        return text

    def _recover_glued_connector_prefixes(self, text: str) -> str:
        # addbanana -> add banana
        # withmilk -> with milk
        # andrice -> and rice
        return re.sub(
            rf"\b({self._CONNECTOR_PATTERN})(?=[a-z])",
            r"\1 ",
            text,
        )

    def _insert_space_between_food_and_number(self, text: str) -> str:
        # apple200g -> apple 200g
        # rice150 -> rice 150
        text = re.sub(r"([a-z])(\d)", r"\1 \2", text)

        # 200gapple -> 200g apple
        # 200apple -> 200 apple
        text = re.sub(r"(\d)([a-z])", r"\1 \2", text)

        return text

    def _normalize_gram_expressions(self, text: str) -> str:
        # 200 g / 200gr / 200 gram / 200 grams -> 200g
        text = re.sub(
            r"(\d+(?:__DECIMAL__\d+)?)\s*(?:g|gr|gram|grams)\b",
            r"\1g",
            text,
        )
        return text

    def _recover_glued_connectors_after_grams(self, text: str) -> str:
        # 100gandbanana -> 100g and banana
        # 100gwithrice -> 100g with rice
        text = re.sub(
            rf"(\d+(?:__DECIMAL__\d+)?g)({self._CONNECTOR_PATTERN})\b",
            r"\1 \2",
            text,
        )
        return text

    def _fix_compact_gram_boundaries(self, text: str) -> str:
        # apple 200grice 150g -> apple 200g rice 150g
        # 100gbanana -> 100g banana
        text = re.sub(r"(\d+(?:__DECIMAL__\d+)?g)(?=[a-z])", r"\1 ", text)
        return text

    def _normalize_spaces(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()