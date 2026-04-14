from difflib import SequenceMatcher
import re
from typing import Optional, Dict, Any, List


class RepeatDetectorService:
    """
    Detects repeated inputs across:
    - current meal memory
    - conversation history (calorie + QA)

    Goals:
    - robust to small formatting differences
    - tolerant to minor typos
    - avoid false positives
    """

    def find_calorie_repeat(
        self,
        input_food: str,
        matched_food: str,
        grams: float,
        meal_state,
        conversation_memory=None,
    ) -> dict:
        meal_match = self._find_in_meal_memory(
            input_food=input_food,
            matched_food=matched_food,
            grams=grams,
            meal_state=meal_state,
        )
        if meal_match is not None:
            return {
                "found": True,
                "repeat_type": "meal_memory",
                "item": meal_match,
            }

        conversation_match = self._find_in_conversation_memory(
            input_food=input_food,
            matched_food=matched_food,
            grams=grams,
            conversation_memory=conversation_memory or [],
        )
        if conversation_match is not None:
            return {
                "found": True,
                "repeat_type": "conversation_memory",
                "item": conversation_match,
            }

        return {
            "found": False,
            "repeat_type": None,
            "item": None,
        }

    def find_qa_repeat(
        self,
        question_text: str,
        conversation_memory=None,
        threshold: float = 0.90,
    ) -> dict:
        conversation_memory = conversation_memory or []
        normalized_question = self._normalize_text(question_text)
        compact_question = self._compact_text(question_text)

        for entry in reversed(conversation_memory):
            if entry.get("kind") != "nutrition_qa":
                continue

            if not self._is_reusable_qa_entry(entry):
                continue

            old_question = self._normalize_text(entry.get("user_input", ""))
            old_compact = self._compact_text(entry.get("user_input", ""))

            if not old_question:
                continue

            if old_question == normalized_question:
                return {
                    "found": True,
                    "repeat_type": "conversation_memory",
                    "item": entry,
                    "similarity": 1.0,
                }

            score = self._similarity(old_compact, compact_question)

            if score >= threshold and self._qa_sanity_check(normalized_question, old_question):
                return {
                    "found": True,
                    "repeat_type": "conversation_memory",
                    "item": entry,
                    "similarity": score,
                }

        return {
            "found": False,
            "repeat_type": None,
            "item": None,
            "similarity": 0.0,
        }

    def _find_in_meal_memory(
        self,
        input_food: str,
        matched_food: str,
        grams: float,
        meal_state,
    ) -> Optional[Dict[str, Any]]:
        normalized_input = self._normalize_text(input_food)
        compact_input = self._compact_text(input_food)
        normalized_matched = self._normalize_text(matched_food)

        for item in meal_state.items:
            if not self._same_quantity(item.grams, grams):
                continue

            existing_food = self._normalize_text(item.food)
            compact_existing = self._compact_text(item.food)

            if existing_food == normalized_matched:
                return self._build_item(item)

            if compact_existing == compact_input:
                return self._build_item(item)

            score = self._similarity(compact_existing, compact_input)
            if score >= 0.92 and self._food_sanity_check(normalized_input, existing_food):
                return self._build_item(item)

        return None

    def _find_in_conversation_memory(
        self,
        input_food: str,
        matched_food: str,
        grams: float,
        conversation_memory,
    ) -> Optional[Dict[str, Any]]:
        compact_input = self._compact_text(input_food)
        normalized_matched = self._normalize_text(matched_food)

        for entry in reversed(conversation_memory):
            if entry.get("kind") != "calorie":
                continue

            items = entry.get("items", []) or []
            for old_item in items:
                old_food = old_item.get("matched_food") or old_item.get("input_food")
                old_grams = old_item.get("grams")

                if old_food is None or old_grams is None:
                    continue

                if not self._same_quantity(old_grams, grams):
                    continue

                normalized_old_food = self._normalize_text(old_food)
                compact_old_food = self._compact_text(old_food)

                if normalized_old_food == normalized_matched:
                    return self._build_item(old_item)

                if compact_old_food == compact_input:
                    return self._build_item(old_item)

                score = self._similarity(compact_old_food, compact_input)
                if score >= 0.92 and self._food_sanity_check(input_food, old_food):
                    return self._build_item(old_item)

        return None

    def _is_reusable_qa_entry(self, entry: dict) -> bool:
        answer = (entry.get("answer") or "").strip().lower()
        confidence = (entry.get("confidence") or "").strip().lower()
        sources_used = entry.get("sources_used", []) or []
        retrieved_contexts = entry.get("retrieved_contexts", []) or []

        if not answer:
            return False

        if confidence == "low":
            return False

        if not sources_used:
            return False

        if not retrieved_contexts:
            return False

        blocked_prefixes = (
            "i could not find enough grounded information",
            "i could not find a sufficiently relevant grounded answer",
            "i could not find a grounded answer",
            "no grounded answer found",
            "your message is empty",
            "please use english for food and nutrition queries",
            "i can see the quantity, but the food name is missing",
            "this looks like a food name, but i could not confidently match it",
            "i recognized a quantity expression, but it is not written with digits",
            "i could not confidently understand your input",
        )

        if any(answer.startswith(prefix) for prefix in blocked_prefixes):
            return False

        return True

    def _same_quantity(self, a: float, b: float) -> bool:
        return abs(float(a) - float(b)) < 1e-6

    def _build_item(self, item) -> Dict[str, Any]:
        return {
            "food": item.get("food") if isinstance(item, dict) else item.food,
            "grams": item.get("grams") if isinstance(item, dict) else item.grams,
            "calories": item.get("calories") if isinstance(item, dict) else item.calories,
            "kcal_per_100g": item.get("kcal_per_100g") if isinstance(item, dict) else item.kcal_per_100g,
        }

    def _food_sanity_check(self, query: str, candidate: str) -> bool:
        q_tokens = self._tokens(query)
        c_tokens = self._tokens(candidate)

        if not q_tokens or not c_tokens:
            return False

        if set(q_tokens) & set(c_tokens):
            return True

        if len(q_tokens) == 1 and len(c_tokens) == 1:
            return q_tokens[0][:3] == c_tokens[0][:3]

        return False

    def _qa_sanity_check(self, q1: str, q2: str) -> bool:
        t1 = set(self._tokens(q1))
        t2 = set(self._tokens(q2))

        if not t1 or not t2:
            return False

        overlap = len(t1 & t2)
        return overlap >= 1

    def _tokens(self, text: str) -> List[str]:
        text = self._normalize_text(text)
        stopwords = {
            "what", "is", "are", "the", "a", "an", "for", "to", "of", "and",
            "in", "on", "does", "do", "can", "i", "my", "with", "it", "be",
            "good", "healthy", "about", "that", "this", "tell", "me",
            "some", "should", "would", "could", "have", "has", "had",
            "food", "foods", "eat", "eating"
        }
        return [t for t in text.split() if len(t) >= 2 and t not in stopwords]

    def _normalize_text(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"[^a-z0-9\s\-]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _compact_text(self, text: str) -> str:
        return self._normalize_text(text).replace(" ", "").replace("-", "")

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()