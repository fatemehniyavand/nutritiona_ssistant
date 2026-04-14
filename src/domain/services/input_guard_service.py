import re


class InputGuardService:
    def classify_input(self, text: str) -> str:
        text = (text or "").strip()

        if not text:
            return "empty"

        if self._contains_non_english_letters(text):
            return "non_english"

        normalized = text.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)

        if self._looks_like_quantity_only(normalized):
            return "quantity_only"

        if self._looks_like_written_quantity_without_digits(normalized):
            return "quantity_not_numeric"

        if self._looks_like_gibberish(normalized):
            return "gibberish"

        if self._looks_like_food_only_candidate(normalized):
            return "food_only"

        return "valid"

    def _contains_non_english_letters(self, text: str) -> bool:
        return bool(re.search(r"[^\x00-\x7F]", text))

    def _looks_like_quantity_only(self, text: str) -> bool:
        patterns = [
            r"^\d+(?:\.\d+)?\s*(g|gram|grams)$",
            r"^\d+(?:\.\d+)?$",
        ]
        return any(re.fullmatch(pattern, text) for pattern in patterns)

    def _looks_like_written_quantity_without_digits(self, text: str) -> bool:
        if re.search(r"\d", text):
            return False

        quantity_words = {
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
            "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
            "eighty", "ninety", "hundred", "thousand",
            "gram", "grams", "g",
        }

        tokens = re.findall(r"[a-zA-Z]+", text)
        if not tokens:
            return False

        quantity_token_count = sum(1 for token in tokens if token in quantity_words)
        return quantity_token_count >= 2

    def _looks_like_food_only_candidate(self, text: str) -> bool:
        if re.search(r"\d", text):
            return False

        command_like_exact = {
            "what is the total now?",
            "what's the total now?",
            "total now",
            "clear meal",
            "show meal",
            "help",
        }
        if text in command_like_exact:
            return False

        command_like_prefixes = (
            "remove ",
            "add ",
            "and ",
            "with ",
            "plus ",
        )
        if text.startswith(command_like_prefixes):
            return False

        tokens = text.split()

        if not (1 <= len(tokens) <= 4):
            return False

        if not all(re.fullmatch(r"[a-zA-Z\-]+", token) for token in tokens):
            return False

        weak_non_food_tokens = {
            "hi", "hello", "hey", "bro", "buddy", "please", "pls", "ok", "okay",
        }
        if all(token in weak_non_food_tokens for token in tokens):
            return False

        # Very short or obviously weak single-token strings should not be treated as food
        if len(tokens) == 1:
            token = tokens[0]

            if len(token) <= 2:
                return False

            if len(set(token)) == 1:
                return False

            vowels = set("aeiou")
            vowel_count = sum(1 for c in token if c in vowels)
            if len(token) >= 3 and vowel_count == 0:
                return False

        return True

    def _looks_like_gibberish(self, text: str) -> bool:
        if len(text) <= 2:
            return True

        alpha_only = re.sub(r"[^a-z]", "", text)

        if not alpha_only:
            return True

        if re.fullmatch(r"[a-z]{1,2}", alpha_only):
            return True

        repetitive_noise = bool(re.fullmatch(r"(.)\1{2,}", alpha_only))
        if repetitive_noise:
            return True

        vowels = set("aeiou")
        vowel_count = sum(1 for c in alpha_only if c in vowels)
        vowel_ratio = vowel_count / max(len(alpha_only), 1)

        weird_clusters = bool(re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", alpha_only))

        if len(alpha_only) >= 6 and vowel_ratio < 0.15 and weird_clusters:
            return True

        # Single short token without vowels is usually noise, not a food
        tokens = text.split()
        if len(tokens) == 1:
            token = re.sub(r"[^a-z]", "", tokens[0])
            if 1 <= len(token) <= 3:
                return True
            if len(token) >= 3 and sum(1 for c in token if c in vowels) == 0:
                return True

        return False