import re
from typing import List, Tuple, Optional

from src.application.services.canonical_calorie_service import CanonicalCalorieService
from src.application.services.daily_calorie_service import DailyCalorieService
from src.application.services.food_resolver_service import FoodResolverService
from src.application.services.meal_memory_service import MealMemoryService
from src.application.services.nlu.food_normalizer import FoodNormalizer
from src.application.services.nlu.food_parser import FoodParser
from src.application.services.repeat_detector_service import RepeatDetectorService
from src.domain.models.meal_state import MealState, MealItem
from src.shared.constants import CALORIE_MODE, HIGH_CONFIDENCE, LOW_CONFIDENCE, MEDIUM_CONFIDENCE


class CalorieItemResponse:
    def __init__(
        self,
        input_food,
        status,
        confidence,
        grams=None,
        matched_food=None,
        kcal_per_100g=None,
        calories=None,
        match_reason=None,
        match_source=None,
        why_rejected=None,
        suggestions=None,
    ):
        self.input_food = input_food
        self.status = status
        self.confidence = confidence
        self.grams = grams
        self.matched_food = matched_food
        self.kcal_per_100g = kcal_per_100g
        self.calories = calories
        self.match_reason = match_reason
        self.match_source = match_source
        self.why_rejected = why_rejected
        self.suggestions = suggestions or []


class CalorieResponse:
    def __init__(
        self,
        items,
        total_calories,
        coverage,
        matched_items,
        total_items,
        confidence,
        final_message,
        suggestions=None,
        meal_state=None,
    ):
        self.mode = CALORIE_MODE
        self.items = items
        self.total_calories = total_calories
        self.coverage = coverage
        self.matched_items = matched_items
        self.total_items = total_items
        self.confidence = confidence
        self.final_message = final_message
        self.suggestions = suggestions or []
        self.meal_state = meal_state


class EstimateMealCalories:
    SAFE_SALVAGE_NOISE_WORDS = {
        "please", "pls", "hey", "hello", "hi", "bro", "buddy",
        "then", "i", "want", "need", "some", "my", "the", "a", "an",
        "fast", "quick", "now", "just", "random", "text", "noise",
        "extra", "words", "word", "blah", "junk", "item", "food",
        "foods", "meal", "also", "maybe", "okay", "ok", "yo",
        "track", "log", "include", "including", "have", "had", "ate", "eat",
        "can", "you", "could", "would", "please", "thanks", "thank", "today",
        "my", "for", "like",
        "can", "you", "could", "would", "please", "thanks", "thank", "today",
        "my", "for", "like",
    }

    TOTAL_QUERY_PATTERNS = [
        r"^what is the total now$",
        r"^what's the total now$",
        r"^whats the total now$",
        r"^what is the total$",
        r"^what's the total$",
        r"^whats the total$",
        r"^total now$",
        r"^current total$",
        r"^meal total$",
        r"^show me the total$",
    ]

    CLEAR_PATTERNS = [
        r"^clear meal$",
        r"^clear the meal$",
        r"^reset meal$",
        r"^empty meal$",
        r"^delete meal$",
    ]

    REMOVE_PATTERN = re.compile(r"^(?:remove|delete|take out)\s+(.+?)$", re.IGNORECASE)

    RECOVERY_PATTERN = re.compile(
        r"([a-z][a-z\s\-']*?)\s+(\d+(?:\.\d+)?)g\b",
        re.IGNORECASE,
    )

    def __init__(self):
        self.meal_memory_service = MealMemoryService()
        self.food_resolver_service = FoodResolverService()
        self.repeat_detector_service = RepeatDetectorService()
        self.food_normalizer = FoodNormalizer()
        self.food_parser = FoodParser()
        self.daily_calorie_service = DailyCalorieService()

    def run(self, text: str, history=None, meal_state=None, conversation_memory=None):
        history = history or []
        meal_state = meal_state or MealState()
        conversation_memory = conversation_memory or []

        normalized = self.food_normalizer.normalize(text)
        normalized_command = self._normalize_command_text(normalized)

        if self._matches_any(normalized_command, self.TOTAL_QUERY_PATTERNS):
            return self._build_total_response(meal_state)

        if self._matches_any(normalized_command, self.CLEAR_PATTERNS):
            self.meal_memory_service.clear(meal_state)
            return CalorieResponse(
                items=[],
                total_calories=0.0,
                coverage="0/0",
                matched_items=0,
                total_items=0,
                confidence=HIGH_CONFIDENCE,
                final_message="Your meal memory has been cleared.",
                suggestions=[],
                meal_state=self._serialize_meal_state(meal_state),
            )

        remove_match = self.REMOVE_PATTERN.match(normalized_command)
        if remove_match:
            food_name = remove_match.group(1).strip()
            self.meal_memory_service.remove_item(meal_state, food_name)

            current_count = len(meal_state.items)
            return CalorieResponse(
                items=[],
                total_calories=meal_state.total_calories,
                coverage=f"{current_count}/{current_count}" if current_count else "0/0",
                matched_items=current_count,
                total_items=current_count,
                confidence=HIGH_CONFIDENCE,
                final_message=(
                    f"Removed '{food_name}' from the current meal. "
                    f"Current meal total is {meal_state.total_calories} kcal."
                ),
                suggestions=[],
                meal_state=self._serialize_meal_state(meal_state),
            )

        cleaned_text = self._normalize_incremental_text(normalized)
        parsed_items, unclear_fragments = self._parse_food_items(cleaned_text)

        if not parsed_items:
            suggestions = []
            for fragment in unclear_fragments:
                suggestions.extend(self.food_resolver_service.suggest(fragment))

            return CalorieResponse(
                items=[],
                total_calories=0.0,
                coverage="0/0",
                matched_items=0,
                total_items=0,
                confidence=LOW_CONFIDENCE,
                final_message="I could not parse any calorie items from your message.",
                suggestions=self._deduplicate_suggestions(suggestions or ["apple", "banana", "rice"]),
                meal_state=self._serialize_meal_state(meal_state),
            )

        response_items: List[CalorieItemResponse] = []
        meal_items_to_add: List[MealItem] = []
        global_suggestions: List[str] = []

        added_count = 0
        updated_count = 0
        repeated_in_meal_count = 0
        repeated_in_conversation_count = 0
        total_attempts = len(parsed_items)

        for food_name, grams, raw_part in parsed_items:
            resolved = self._resolve_food_scientifically(food_name)

            if not resolved["matched"]:
                best_food, leftover_noise = self._extract_best_food_candidate(food_name)

                if best_food and best_food != food_name:
                    resolved = self._resolve_food_scientifically(best_food)
                    if leftover_noise:
                        global_suggestions.extend(self.food_resolver_service.suggest(leftover_noise))

                if resolved["matched"]:
                    food_name = best_food

            if not resolved["matched"]:
                suggestions = self.food_resolver_service.suggest(food_name)
                response_items.append(
                    CalorieItemResponse(
                        input_food=food_name,
                        status="not_found",
                        confidence=LOW_CONFIDENCE,
                        grams=grams,
                        matched_food=None,
                        kcal_per_100g=None,
                        calories=None,
                        why_rejected="Food not found in the current calorie database.",
                        suggestions=suggestions,
                    )
                )
                global_suggestions.extend(suggestions[:3])
                continue

            matched_food = resolved["matched_food"]
            kcal_per_100g = float(resolved["kcal_per_100g"])
            calories = round((float(grams) * kcal_per_100g) / 100.0, 2)

            repeat_result = self.repeat_detector_service.find_calorie_repeat(
                input_food=food_name,
                matched_food=matched_food,
                grams=grams,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )

            if repeat_result["found"]:
                repeat_item = repeat_result["item"]

                if repeat_result["repeat_type"] == "meal_memory_exact":
                    repeated_in_meal_count += 1

                    response_items.append(
                        CalorieItemResponse(
                            input_food=food_name,
                            status="matched",
                            confidence=HIGH_CONFIDENCE,
                            grams=repeat_item["grams"],
                            matched_food=repeat_item["food"],
                            kcal_per_100g=repeat_item["kcal_per_100g"],
                            calories=repeat_item["calories"],
                            match_reason=(
                                f"As I told you before, this item is already in your current meal. "
                                f"Normalized and matched to '{repeat_item['food']}'."
                            ),
                            match_source="meal_memory_exact",
                            suggestions=[f"remove {repeat_item['food']}", "clear meal"],
                        )
                    )
                    continue

                if repeat_result["repeat_type"] == "meal_memory_update":
                    updated_count += 1
                    previous_grams = repeat_item["grams"]

                    updated_item = self.meal_memory_service.add_or_update_item(
                        meal_state,
                        MealItem(
                            food=matched_food,
                            grams=grams,
                            calories=calories,
                            kcal_per_100g=kcal_per_100g,
                        )
                    )

                    response_items.append(
                        CalorieItemResponse(
                            input_food=food_name,
                            status="matched",
                            confidence=HIGH_CONFIDENCE,
                            grams=updated_item.grams,
                            matched_food=updated_item.food,
                            kcal_per_100g=updated_item.kcal_per_100g,
                            calories=updated_item.calories,
                            match_reason=(
                                f"As I told you before, I had already seen '{updated_item.food}' in your current meal. "
                                f"I updated it from {self._format_grams(previous_grams)}g "
                                f"to {self._format_grams(updated_item.grams)}g."
                            ),
                            match_source="meal_memory_update",
                            suggestions=[f"remove {updated_item.food}", "clear meal"],
                        )
                    )
                    continue

                if repeat_result["repeat_type"] == "conversation_memory_exact":
                    repeated_in_conversation_count += 1

                    old_kcal = repeat_item.get("kcal_per_100g")
                    old_calories = repeat_item.get("calories")
                    repeat_food = repeat_item["food"]
                    repeat_grams = repeat_item["grams"]

                    response_items.append(
                        CalorieItemResponse(
                            input_food=food_name,
                            status="matched",
                            confidence=HIGH_CONFIDENCE,
                            grams=repeat_grams,
                            matched_food=repeat_food,
                            kcal_per_100g=old_kcal if old_kcal is not None else kcal_per_100g,
                            calories=old_calories if old_calories is not None else calories,
                            match_reason=(
                                f"As I told you before, I already answered this item earlier in the conversation. "
                                f"Normalized and matched to '{repeat_food}'."
                            ),
                            match_source="conversation_memory_exact",
                            suggestions=[
                                f"add {repeat_food} {self._format_grams(repeat_grams)}g",
                                "clear meal",
                            ],
                        )
                    )
                    continue

            response_items.append(
                CalorieItemResponse(
                    input_food=food_name,
                    status="matched",
                    confidence=resolved["confidence"],
                    grams=grams,
                    matched_food=matched_food,
                    kcal_per_100g=kcal_per_100g,
                    calories=calories,
                    match_reason=resolved.get("match_reason"),
                    match_source=resolved.get("match_source"),
                    suggestions=resolved.get("suggestions", []) or [],
                )
            )

            meal_items_to_add.append(
                MealItem(
                    food=matched_food,
                    grams=grams,
                    calories=calories,
                    kcal_per_100g=kcal_per_100g,
                )
            )
            added_count += 1

        if meal_items_to_add:
            self.meal_memory_service.add_items(meal_state, meal_items_to_add)
            self.daily_calorie_service.log_items_today(meal_items_to_add)
            meal_state.last_input = text

        matched_items_only = [
            item for item in response_items
            if item.status == "matched" and item.calories is not None
        ]

        matched_count = len(matched_items_only)
        confidence = self._overall_confidence(matched_count, total_attempts)

        response_total_calories = round(
            sum(float(item.calories) for item in matched_items_only),
            2,
        )

        for fragment in unclear_fragments:
            global_suggestions.extend(self.food_resolver_service.suggest(fragment))

        final_message = self._build_final_message(
            meal_state=meal_state,
            matched_count=matched_count,
            total_count=total_attempts,
            added_count=added_count,
            updated_count=updated_count,
            repeated_in_meal_count=repeated_in_meal_count,
            repeated_in_conversation_count=repeated_in_conversation_count,
            has_unclear=bool(unclear_fragments),
            response_items=response_items,
        )

        return CalorieResponse(
            items=response_items,
            total_calories=response_total_calories,
            coverage=f"{matched_count}/{total_attempts}",
            matched_items=matched_count,
            total_items=total_attempts,
            confidence=confidence,
            final_message=final_message,
            suggestions=self._deduplicate_suggestions(global_suggestions),
            meal_state=self._serialize_meal_state(meal_state),
        )

    def _resolve_food_scientifically(self, food_name: str) -> dict:
        canonical_name = CanonicalCalorieService.normalize_food_name(food_name)
        canonical_kcal = CanonicalCalorieService.get_calories_per_100g(canonical_name)

        if canonical_kcal is not None:
            return {
                "matched": True,
                "matched_food": canonical_name,
                "kcal_per_100g": float(canonical_kcal),
                "confidence": HIGH_CONFIDENCE,
                "match_reason": "Canonical benchmark nutrition value used for reproducible evaluation.",
                "match_source": "canonical_calorie_table",
                "suggestions": [],
            }

        resolved = self.food_resolver_service.resolve(food_name)

        if not resolved.get("matched"):
            return resolved

        matched_food = resolved.get("matched_food") or food_name
        matched_canonical = CanonicalCalorieService.normalize_food_name(matched_food)
        matched_canonical_kcal = CanonicalCalorieService.get_calories_per_100g(matched_canonical)

        if matched_canonical_kcal is not None:
            return {
                "matched": True,
                "matched_food": matched_canonical,
                "kcal_per_100g": float(matched_canonical_kcal),
                "confidence": HIGH_CONFIDENCE,
                "match_reason": "Canonical benchmark nutrition value used after resolver normalization.",
                "match_source": "canonical_after_resolver",
                "suggestions": resolved.get("suggestions", []) or [],
            }

        return resolved

    def _build_total_response(self, meal_state: MealState):
        if not meal_state.items:
            return CalorieResponse(
                items=[],
                total_calories=0.0,
                coverage="0/0",
                matched_items=0,
                total_items=0,
                confidence=MEDIUM_CONFIDENCE,
                final_message="Your current meal is empty.",
                suggestions=["Try: apple 200g", "Try: add banana 100g"],
                meal_state=self._serialize_meal_state(meal_state),
            )

        response_items = []
        for item in meal_state.items:
            response_items.append(
                CalorieItemResponse(
                    input_food=item.food,
                    status="matched",
                    confidence=HIGH_CONFIDENCE,
                    grams=item.grams,
                    matched_food=item.food,
                    kcal_per_100g=item.kcal_per_100g,
                    calories=item.calories,
                    match_reason="Retrieved from current meal memory.",
                    match_source="meal_memory",
                    suggestions=[],
                )
            )

        current_count = len(meal_state.items)
        return CalorieResponse(
            items=response_items,
            total_calories=meal_state.total_calories,
            coverage=f"{current_count}/{current_count}",
            matched_items=current_count,
            total_items=current_count,
            confidence=HIGH_CONFIDENCE,
            final_message="Returned total calories from the current meal memory.",
            suggestions=[],
            meal_state=self._serialize_meal_state(meal_state),
        )

    def _serialize_meal_state(self, meal_state: MealState) -> dict:
        return {
            "total_calories": float(getattr(meal_state, "total_calories", 0.0) or 0.0),
            "last_input": getattr(meal_state, "last_input", "") or "",
            "items": [
                {
                    "food": item.food,
                    "grams": float(item.grams),
                    "calories": float(item.calories),
                    "kcal_per_100g": float(item.kcal_per_100g),
                }
                for item in getattr(meal_state, "items", [])
            ],
            "matched_items": len(getattr(meal_state, "items", [])),
            "total_items": len(getattr(meal_state, "items", [])),
        }

    def _normalize_incremental_text(self, text: str) -> str:
        text = (text or "").strip()

        for prefix in ("and ", "add ", "with ", "plus "):
            if text.startswith(prefix):
                return text[len(prefix):].strip()

        return text

    def _parse_food_items(self, text: str) -> Tuple[List[Tuple[str, float, str]], List[str]]:
        text = self.food_normalizer.normalize(text)

        parsed = self.food_parser.parse_food_items(text)
        leftovers = self.food_parser.extract_unparsed_text(text, parsed)

        parsed_items: List[Tuple[str, float, str]] = []
        unclear_fragments: List[str] = []
        seen_signatures = set()

        def add_parsed_item(food_name: str, grams: float, raw_text: str):
            normalized_food = (food_name or "").strip().lower()
            if not normalized_food:
                return

            signature = (normalized_food, round(float(grams), 4))
            if signature in seen_signatures:
                return

            seen_signatures.add(signature)
            parsed_items.append((normalized_food, float(grams), raw_text))

        for item in parsed:
            cleaned_phrase = self._strip_common_noise_prefixes(item.food_name)
            if not cleaned_phrase:
                continue

            best_food, leftover_noise = self._extract_best_food_candidate(cleaned_phrase)
            chosen_food = best_food if best_food else cleaned_phrase

            add_parsed_item(chosen_food, item.grams, item.raw_text)

            if leftover_noise:
                unclear_fragments.append(leftover_noise)

        if leftovers:
            for match in self.RECOVERY_PATTERN.finditer(leftovers):
                raw_food_phrase = match.group(1).strip()
                grams = float(match.group(2))

                cleaned_phrase = self._strip_common_noise_prefixes(raw_food_phrase)
                if not cleaned_phrase:
                    continue

                best_food, leftover_noise = self._extract_best_food_candidate(cleaned_phrase)
                chosen_food = best_food if best_food else cleaned_phrase
                add_parsed_item(chosen_food, grams, match.group(0).strip())

                if leftover_noise:
                    unclear_fragments.append(leftover_noise)

            cleaned_leftover = leftovers.strip()
            if cleaned_leftover:
                unclear_fragments.extend(self._split_unclear_fragments(cleaned_leftover))

        return parsed_items, self._deduplicate_fragments(unclear_fragments)

    def _split_unclear_fragments(self, text: str) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []

        chunks = [
            c.strip()
            for c in re.split(r"\s+(?:and|plus|with|add)\s+|,", text)
            if c.strip()
        ]
        return chunks if chunks else [text]

    def _strip_common_noise_prefixes(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        words = text.split()
        while words and words[0].lower() in self.SAFE_SALVAGE_NOISE_WORDS:
            words.pop(0)

        return " ".join(words).strip()

    def _extract_best_food_candidate(self, raw_food_phrase: str) -> Tuple[Optional[str], str]:
        raw_food_phrase = (raw_food_phrase or "").strip()
        if not raw_food_phrase:
            return None, ""

        resolved_full = self._resolve_food_scientifically(raw_food_phrase)
        if resolved_full["matched"]:
            return raw_food_phrase, ""

        words = raw_food_phrase.split()
        if not words:
            return None, ""

        max_len = min(5, len(words))

        for length in range(max_len, 0, -1):
            for start in range(0, len(words) - length + 1):
                candidate_words = words[start:start + length]
                prefix_words = words[:start]
                suffix_words = words[start + length:]

                candidate = " ".join(candidate_words).strip()
                noise_words = prefix_words + suffix_words
                noise = " ".join(noise_words).strip()

                if not self._is_safe_salvage_noise(noise_words):
                    continue

                resolved = self._resolve_food_scientifically(candidate)
                if resolved["matched"]:
                    return candidate, noise

        return None, raw_food_phrase

    def _is_safe_salvage_noise(self, noise_words: List[str]) -> bool:
        if not noise_words:
            return True

        for word in noise_words:
            word = (word or "").strip().lower()
            if not word:
                continue

            if word in self.SAFE_SALVAGE_NOISE_WORDS:
                continue

            if len(word) <= 2:
                continue

            if re.fullmatch(r"[a-z]*\d+[a-z\d]*", word):
                continue

            return False

        return True

    def _overall_confidence(self, matched_count: int, total_count: int) -> str:
        if total_count == 0:
            return LOW_CONFIDENCE
        if matched_count == total_count:
            return HIGH_CONFIDENCE
        if matched_count >= 1:
            return MEDIUM_CONFIDENCE
        return LOW_CONFIDENCE

    def _build_final_message(
        self,
        meal_state: MealState,
        matched_count: int,
        total_count: int,
        added_count: int,
        updated_count: int,
        repeated_in_meal_count: int,
        repeated_in_conversation_count: int,
        has_unclear: bool,
        response_items,
    ) -> str:
        if total_count == 0:
            return "No items were added to the current meal."

        if matched_count == 0 and has_unclear:
            return (
                "I found text that looks unclear or misspelled. "
                "Please rewrite the unclear part and keep the valid food + grams format, "
                "for example: 'apple 200g'."
            )

        if matched_count == 0:
            return "I could not match any items, so the current meal was not updated."

        total_repeats = repeated_in_meal_count + repeated_in_conversation_count

        if total_count == 1 and total_repeats == 1 and added_count == 0 and updated_count == 0:
            item = response_items[0]
            grams_display = self._format_grams(item.grams)

            if item.match_source == "meal_memory_exact":
                return (
                    f"As I told you before, {item.matched_food} {grams_display}g is "
                    f"{item.calories} kcal and it is already in your current meal."
                )

            if item.match_source == "conversation_memory_exact":
                return (
                    f"As I told you before, {item.matched_food} {grams_display}g is "
                    f"{item.calories} kcal. It was already answered earlier in this conversation."
                )

        if total_count == 1 and updated_count == 1 and added_count == 0:
            item = response_items[0]
            return (
                f"As I told you before, I had already seen '{item.matched_food}' in your meal memory. "
                f"It has now been updated to {self._format_grams(item.grams)}g "
                f"({item.calories} kcal). Current meal total is {meal_state.total_calories} kcal."
            )

        if added_count > 0 and updated_count > 0 and has_unclear:
            return (
                f"I updated {updated_count} existing item(s) and added {added_count} new item(s), "
                f"but some extra text looked unclear or misspelled. "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        if added_count > 0 and updated_count > 0:
            return (
                f"I updated {updated_count} existing item(s) and added {added_count} new item(s). "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        if updated_count > 0 and added_count == 0:
            return (
                f"I saw {updated_count} food item(s) before and updated their amounts in your current meal. "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        if added_count > 0 and has_unclear:
            return (
                f"I recognized the valid food part and added {added_count} item(s), "
                f"but some extra text looked unclear or misspelled. "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        if added_count > 0 and total_repeats > 0:
            return (
                f"I recognized {total_repeats} item(s) that were already known and added "
                f"{added_count} new item(s). Current meal total is {meal_state.total_calories} kcal."
            )

        if total_repeats > 0 and added_count == 0 and updated_count == 0:
            return (
                "As I told you before, these item(s) were already answered earlier. "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        if matched_count < total_count:
            return (
                "I added the recognized item(s), but some parts were not clear enough. "
                f"Current meal total is {meal_state.total_calories} kcal."
            )

        return f"Meal updated successfully. Current meal total is {meal_state.total_calories} kcal."

    def _format_grams(self, grams) -> str:
        grams = float(grams)
        return str(int(grams)) if grams.is_integer() else str(grams)

    def _deduplicate_suggestions(self, suggestions: List[str]) -> List[str]:
        unique = []
        seen = set()

        for suggestion in suggestions:
            normalized = (suggestion or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(suggestion)

        return unique[:6]

    def _deduplicate_fragments(self, fragments: List[str]) -> List[str]:
        unique = []
        seen = set()

        for fragment in fragments:
            normalized = (fragment or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(fragment.strip())

        return unique

    def _normalize_command_text(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)