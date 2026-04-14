import re
from typing import Any, Iterable

from src.application.dto.responses import QAResponse
from src.application.services.food_resolver_service import FoodResolverService
from src.application.services.meal_memory_service import MealMemoryService
from src.application.services.memory_service import MemoryService
from src.application.services.nlu.nlu_service import NutritionNLUService
from src.application.services.repeat_detector_service import RepeatDetectorService
from src.application.use_cases.answer_nutrition_question import AnswerNutritionQuestion
from src.application.use_cases.estimate_meal_calories import EstimateMealCalories
from src.domain.services.input_guard_service import InputGuardService
from src.shared.constants import CALORIE_MODE, LOW_CONFIDENCE, QNA_MODE


class NutritionOrchestrator:
    def __init__(self):
        self.calorie_use_case = EstimateMealCalories()
        self.qa_use_case = AnswerNutritionQuestion()
        self.input_guard = InputGuardService()
        self.memory_service = MemoryService(similarity_threshold=0.82)
        self.meal_memory_service = MealMemoryService()
        self.nlu_service = NutritionNLUService()
        self.repeat_detector_service = RepeatDetectorService()
        self.food_resolver_service = FoodResolverService()

    def detect_mode(self, text: str) -> str:
        normalized = (text or "").strip().lower()

        calorie_patterns = [
            r"\d+(?:\.\d+)?\s*g\b",
            r"\badd\b",
            r"\band\b",
            r"\bwith\b",
            r"\bplus\b",
            r"\bremove\b",
            r"\bclear meal\b",
            r"\btotal now\b",
            r"\bwhat is the total now\b",
        ]

        for pattern in calorie_patterns:
            if re.search(pattern, normalized):
                return CALORIE_MODE

        return QNA_MODE

    def run(
        self,
        text: str,
        history=None,
        memory_entries=None,
        meal_state=None,
        conversation_memory=None,
    ):
        history = history or []
        memory_entries = memory_entries or []
        conversation_memory = conversation_memory or []

        nlu_result = self.nlu_service.parse(text)
        original_text = (nlu_result.original_text or "").strip()
        normalized = (nlu_result.normalized_text or "").strip()
        intent = (nlu_result.intent or "").strip().lower()

        guard_bypass_intents = {
            "total_query",
            "clear_meal",
            "remove_item",
        }

        guard_input = normalized
        if not normalized and original_text:
            guard_input = original_text

        input_class = self.input_guard.classify_input(guard_input)

        if intent in guard_bypass_intents:
            return self.calorie_use_case.run(
                normalized,
                history=history,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )

        if intent == "nutrition_qa":
            if input_class in {"empty", "non_english"}:
                repeated_guard = self._find_repeated_non_answer_case(
                    normalized=normalized or original_text.lower().strip(),
                    conversation_memory=conversation_memory,
                )
                if repeated_guard is not None:
                    return repeated_guard
                return self._build_guard_response(input_class, original_text or normalized)

            repeated_qa = self._try_reuse_previous_qa(
                normalized=normalized,
                memory_entries=memory_entries,
                conversation_memory=conversation_memory,
            )
            if repeated_qa is not None:
                return repeated_qa

            return self.qa_use_case.run(
                normalized,
                history=history,
                conversation_memory=conversation_memory,
            )

        if input_class != "valid":
            repeated_guard = self._find_repeated_non_answer_case(
                normalized=normalized or original_text.lower().strip(),
                conversation_memory=conversation_memory,
            )
            if repeated_guard is not None:
                return repeated_guard

            return self._build_guard_response(input_class, original_text or normalized)

        if intent == "calorie_input":
            return self.calorie_use_case.run(
                normalized,
                history=history,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )

        if intent == "empty":
            return self._build_guard_response("empty", original_text or normalized)

        return self._build_guard_response("gibberish", original_text or normalized)

    def _try_reuse_previous_qa(self, normalized: str, memory_entries, conversation_memory) -> QAResponse | None:
        repeat_match = self.repeat_detector_service.find_qa_repeat(
            question_text=normalized,
            conversation_memory=conversation_memory,
            threshold=0.90,
        )

        if repeat_match["found"] and repeat_match["item"]:
            old_entry = repeat_match["item"]

            if self._is_reusable_qa_entry_dict(old_entry):
                reused_answer = old_entry.get("answer", "")

                return QAResponse(
                    mode=QNA_MODE,
                    answer=reused_answer,
                    confidence=old_entry.get("confidence", LOW_CONFIDENCE),
                    sources_used=old_entry.get("sources_used", []) or [],
                    retrieved_contexts=old_entry.get("retrieved_contexts", []) or [],
                    final_message=(
                        f"As I told you before, this question was already answered earlier "
                        f"in the conversation (similarity={repeat_match['similarity']:.2f})."
                    ),
                )

        memory_match = self.memory_service.find_similar_question(
            current_question=normalized,
            memory_entries=memory_entries,
            mode=QNA_MODE,
        )

        if memory_match.found and memory_match.matched_entry:
            if self._is_reusable_memory_entry(memory_match.matched_entry):
                reused_answer = self.memory_service.build_memory_based_answer(
                    memory_match.matched_entry
                )

                return QAResponse(
                    mode=QNA_MODE,
                    answer=reused_answer,
                    confidence=memory_match.matched_entry.confidence,
                    sources_used=memory_match.matched_entry.sources_used,
                    retrieved_contexts=[],
                    final_message=(
                        f"As I told you before, I already answered a very similar question "
                        f"(similarity={memory_match.similarity_score:.2f})."
                    ),
                )

        return None

    def _is_reusable_qa_entry_dict(self, entry: dict[str, Any]) -> bool:
        answer = (entry.get("answer") or "").strip().lower()
        confidence = (entry.get("confidence") or LOW_CONFIDENCE).strip().lower()
        sources_used = entry.get("sources_used", []) or []
        retrieved_contexts = entry.get("retrieved_contexts", []) or []

        if confidence == LOW_CONFIDENCE.lower():
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
        )

        if any(answer.startswith(prefix) for prefix in blocked_prefixes):
            return False

        return True

    def _is_reusable_memory_entry(self, entry) -> bool:
        answer = (getattr(entry, "answer", "") or "").strip().lower()
        confidence = (getattr(entry, "confidence", LOW_CONFIDENCE) or LOW_CONFIDENCE).strip().lower()
        sources_used = getattr(entry, "sources_used", []) or []

        if confidence == LOW_CONFIDENCE.lower():
            return False

        if not sources_used:
            return False

        blocked_prefixes = (
            "i could not find enough grounded information",
            "i could not find a sufficiently relevant grounded answer",
            "i could not find a grounded answer",
            "no grounded answer found",
        )

        if any(answer.startswith(prefix) for prefix in blocked_prefixes):
            return False

        return True

    def _find_repeated_non_answer_case(
        self,
        normalized: str,
        conversation_memory: Iterable[dict[str, Any]],
    ) -> QAResponse | None:
        if not normalized:
            return None

        normalized = normalized.strip().lower()

        for entry in reversed(list(conversation_memory or [])):
            previous_input = (entry.get("normalized_input") or "").strip().lower()
            previous_answer = (entry.get("answer") or "").strip()
            previous_kind = (entry.get("kind") or "").strip().lower()

            if previous_input != normalized:
                continue

            if previous_kind != QNA_MODE:
                continue

            if not previous_answer:
                continue

            if previous_answer not in {
                "Your message is empty.",
                "Please use English for food and nutrition queries.",
                "I can see the quantity, but the food name is missing.",
                "This looks like a food name, but I could not confidently match it.",
                "I recognized a quantity expression, but it is not written with digits.",
                "I could not confidently understand your input.",
            } and not (
                previous_answer.startswith("I recognized '")
                and "but I still need the quantity in grams." in previous_answer
            ):
                continue

            return QAResponse(
                mode=QNA_MODE,
                answer=previous_answer,
                confidence=entry.get("confidence", LOW_CONFIDENCE),
                sources_used=entry.get("sources_used", []) or [],
                retrieved_contexts=entry.get("retrieved_contexts", []) or [],
                final_message="As I told you before, this input pattern was already handled earlier.",
            )

        return None

    def _build_guard_response(self, input_class: str, original_text: str) -> QAResponse:
        clean_text = (original_text or "").strip()

        if input_class == "empty":
            return QAResponse(
                mode=QNA_MODE,
                answer="Your message is empty.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Type a food query or a nutrition question in English. Example: 'apple 200g'.",
            )

        if input_class == "non_english":
            return QAResponse(
                mode=QNA_MODE,
                answer="Please use English for food and nutrition queries.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Example: 'apple 200g' or 'Is avocado healthy?'",
            )

        if input_class == "quantity_only":
            return QAResponse(
                mode=QNA_MODE,
                answer="I can see the quantity, but the food name is missing.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please provide both the food name and the amount. Example: 'apple 200g' or 'rice 150g'.",
            )

        if input_class == "food_only":
            resolved = self.food_resolver_service.resolve(clean_text)

            if resolved.get("matched"):
                matched_food = resolved.get("matched_food") or clean_text
                return QAResponse(
                    mode=QNA_MODE,
                    answer=f"I recognized '{matched_food}', but I still need the quantity in grams.",
                    confidence=LOW_CONFIDENCE,
                    sources_used=[],
                    retrieved_contexts=[],
                    final_message=f"Try: '{matched_food} 200g'.",
                )

            suggestions = resolved.get("suggestions", []) or []
            if suggestions:
                suggestion_text = ", ".join([f"'{s}'" for s in suggestions[:3]])
                return QAResponse(
                    mode=QNA_MODE,
                    answer="This looks like a food name, but I could not confidently match it.",
                    confidence=LOW_CONFIDENCE,
                    sources_used=[],
                    retrieved_contexts=[],
                    final_message=(
                        f"I may not have understood the food name correctly. "
                        f"Did you mean {suggestion_text}? Example: '{suggestions[0]} 200g'."
                    ),
                )

            return QAResponse(
                mode=QNA_MODE,
                answer="This looks like a food name, but I could not confidently match it.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please type a clear English food name and quantity, for example: 'apple 200g'.",
            )

        if input_class == "quantity_not_numeric":
            return QAResponse(
                mode=QNA_MODE,
                answer="I recognized a quantity expression, but it is not written with digits.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please write the amount with digits, for example: 'apple 200g' instead of 'apple two hundred grams'.",
            )

        if input_class == "gibberish":
            return QAResponse(
                mode=QNA_MODE,
                answer="I could not confidently understand your input.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please write a clear food + grams query or a nutrition question, for example: 'banana 120g' or 'Is avocado healthy?'",
            )

        return QAResponse(
            mode=QNA_MODE,
            answer="This assistant only handles food, calories, and nutrition.",
            confidence=LOW_CONFIDENCE,
            sources_used=[],
            retrieved_contexts=[],
            final_message="Try something like 'apple 200g' or 'What are good sources of protein?'",
        )