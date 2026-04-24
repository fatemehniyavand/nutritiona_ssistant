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
from src.domain.models.meal_state import MealState
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

        self._session_history = []
        self._session_memory_entries = []
        self._session_meal_state = MealState()
        self._session_conversation_memory = []

    def reset_session_state(self) -> None:
        self._session_history = []
        self._session_memory_entries = []
        self._session_meal_state = MealState()
        self._session_conversation_memory = []

    def detect_mode(self, text: str) -> str:
        nlu_result = self.nlu_service.parse(text)
        if nlu_result.intent in {"calorie_input", "clear_meal", "remove_item", "total_query"}:
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
        using_internal_history = history is None
        using_internal_memory_entries = memory_entries is None
        using_internal_meal_state = meal_state is None
        using_internal_conversation_memory = conversation_memory is None

        history = self._session_history if using_internal_history else history
        memory_entries = self._session_memory_entries if using_internal_memory_entries else memory_entries
        meal_state = self._session_meal_state if using_internal_meal_state else meal_state
        conversation_memory = (
            self._session_conversation_memory
            if using_internal_conversation_memory
            else conversation_memory
        )

        nlu_result = self.nlu_service.parse(text)
        original_text = (nlu_result.original_text or "").strip()
        normalized = (nlu_result.normalized_text or "").strip()
        intent = (nlu_result.intent or "").strip().lower()

        pre_guard_class = self._pre_route_guard_class(original_text, normalized)

        if pre_guard_class != "valid":
            repeated_guard = self._find_repeated_non_answer_case(
                normalized=normalized or original_text.lower().strip(),
                conversation_memory=conversation_memory,
            )
            response = repeated_guard or self._build_guard_response(
                pre_guard_class,
                original_text or normalized,
            )
            self._record_turn(
                user_input=text,
                normalized_input=normalized or original_text.lower().strip(),
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        guard_bypass_intents = {"total_query", "clear_meal", "remove_item"}

        if intent in guard_bypass_intents:
            response = self.calorie_use_case.run(
                normalized,
                history=history,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="calorie",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if intent == "empty":
            repeated_guard = self._find_repeated_non_answer_case(
                normalized=normalized or original_text.lower().strip(),
                conversation_memory=conversation_memory,
            )
            response = repeated_guard or self._build_guard_response("empty", original_text)
            self._record_turn(
                user_input=text,
                normalized_input=normalized or original_text.lower().strip(),
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if nlu_result.is_quantity_not_numeric:
            response = self._build_guard_response("quantity_not_numeric", original_text)
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if nlu_result.is_quantity_only:
            response = self._build_guard_response("quantity_only", original_text)
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if nlu_result.is_food_only:
            response = self._build_guard_response("food_only", normalized or original_text)
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if intent == "calorie_input" and nlu_result.parsed_items:
            response = self.calorie_use_case.run(
                normalized,
                history=history,
                meal_state=meal_state,
                conversation_memory=conversation_memory,
            )
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="calorie",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if intent == "calorie_input" and not nlu_result.parsed_items:
            repeated_guard = self._find_repeated_non_answer_case(
                normalized=normalized or original_text.lower().strip(),
                conversation_memory=conversation_memory,
            )
            response = repeated_guard or self._build_guard_response("gibberish", original_text or normalized)
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        if intent == "nutrition_qa":
            guard_input = normalized if normalized else original_text
            input_class = self.input_guard.classify_input(guard_input)

            if input_class in {"empty", "non_english"}:
                repeated_guard = self._find_repeated_non_answer_case(
                    normalized=normalized or original_text.lower().strip(),
                    conversation_memory=conversation_memory,
                )
                response = repeated_guard or self._build_guard_response(input_class, original_text or normalized)
                self._record_turn(
                    user_input=text,
                    normalized_input=normalized,
                    kind="guard",
                    response=response,
                    history=history,
                    conversation_memory=conversation_memory,
                )
                return response

            repeated_qa = self._try_reuse_previous_qa(
                normalized=normalized,
                memory_entries=memory_entries,
                conversation_memory=conversation_memory,
            )
            if repeated_qa is not None:
                self._record_turn(
                    user_input=text,
                    normalized_input=normalized,
                    kind=QNA_MODE,
                    response=repeated_qa,
                    history=history,
                    conversation_memory=conversation_memory,
                )
                return repeated_qa

            qa_response = self.qa_use_case.run(
                normalized,
                history=history,
                conversation_memory=conversation_memory,
            )

            fallback_repeat = self._recover_repeat_after_failed_qa(
                normalized=normalized,
                qa_response=qa_response,
                conversation_memory=conversation_memory,
            )
            response = fallback_repeat or qa_response

            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind=QNA_MODE,
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        guard_input = normalized if normalized else original_text
        input_class = self.input_guard.classify_input(guard_input)

        if input_class != "valid":
            repeated_guard = self._find_repeated_non_answer_case(
                normalized=normalized or original_text.lower().strip(),
                conversation_memory=conversation_memory,
            )
            response = repeated_guard or self._build_guard_response(input_class, original_text or normalized)
            self._record_turn(
                user_input=text,
                normalized_input=normalized,
                kind="guard",
                response=response,
                history=history,
                conversation_memory=conversation_memory,
            )
            return response

        response = self._build_guard_response("gibberish", original_text or normalized)
        self._record_turn(
            user_input=text,
            normalized_input=normalized,
            kind="guard",
            response=response,
            history=history,
            conversation_memory=conversation_memory,
        )
        return response

    def _pre_route_guard_class(self, original_text: str, normalized_text: str) -> str:
        text = original_text or ""
        normalized = (normalized_text or text).strip().lower()

        if not text.strip():
            return "empty"

        if re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF۰-۹]", text):
            return "non_english"

        if re.search(r"\b[a-z][a-z\s'\-]*\s+-\d+(?:\.\d+)?\s*g\b", normalized):
            return "invalid_quantity"

        if re.search(r"\b[a-z][a-z\s'\-]*\s+0(?:\.0+)?\s*g\b", normalized):
            return "invalid_quantity"

        if re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand)\b.*\b(gram|grams|g)\b",
            normalized,
        ):
            return "quantity_not_numeric"

        if re.search(r"\b(one|two|three|a glass of|glass of|cup of|piece of)\b", normalized):
            if not re.search(r"\d+(?:\.\d+)?\s*g\b", normalized):
                return "quantity_not_numeric"

        unsafe_patterns = [
            r"\blose\s+\d+\s*kg\s+in\s+one\s+week\b",
            r"\blose weight fast\b",
            r"\bstarvation diet\b",
            r"\bstop eating\b",
            r"\bnot eating\b",
            r"\bextreme diet\b",
            r"\bdangerous diet\b",
        ]
        if any(re.search(pattern, normalized) for pattern in unsafe_patterns):
            return "unsafe"

        irrelevant_patterns = [
            r"\bpresident\b",
            r"\bfootball score\b",
            r"\bweather\b",
            r"\bpython code\b",
            r"\bwrite me code\b",
            r"\bhack\b",
            r"\bpassword\b",
            r"\bcrypto\b",
            r"\bmovie\b",
            r"\bgame\b",
        ]
        if any(re.search(pattern, normalized) for pattern in irrelevant_patterns):
            return "out_of_domain"

        return "valid"

    def _record_turn(
        self,
        user_input: str,
        normalized_input: str,
        kind: str,
        response,
        history,
        conversation_memory,
    ) -> None:
        response_dict = self._response_to_dict(response)

        history.append(
            {
                "user_input": user_input,
                "normalized_input": normalized_input,
                "kind": kind,
                "response": response_dict,
            }
        )

        conversation_entry = {
            "user_input": user_input,
            "normalized_input": normalized_input,
            "kind": kind,
            "answer": response_dict.get("answer", "") or response_dict.get("final_message", ""),
            "confidence": response_dict.get("confidence", ""),
            "sources_used": response_dict.get("sources_used", []) or [],
            "retrieved_contexts": response_dict.get("retrieved_contexts", []) or [],
            "items": response_dict.get("items", []) or [],
            "final_message": response_dict.get("final_message", ""),
            "mode": response_dict.get("mode", ""),
        }
        conversation_memory.append(conversation_entry)

    def _response_to_dict(self, response) -> dict:
        if isinstance(response, dict):
            return response

        data = {}
        for key in dir(response):
            if key.startswith("_"):
                continue
            value = getattr(response, key, None)
            if callable(value):
                continue
            data[key] = value

        if "items" in data and data["items"]:
            normalized_items = []
            for item in data["items"]:
                if isinstance(item, dict):
                    normalized_items.append(item)
                else:
                    item_dict = {}
                    for k in dir(item):
                        if k.startswith("_"):
                            continue
                        v = getattr(item, k, None)
                        if callable(v):
                            continue
                        item_dict[k] = v
                    normalized_items.append(item_dict)
            data["items"] = normalized_items

        return data

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

    def _recover_repeat_after_failed_qa(
        self,
        normalized: str,
        qa_response,
        conversation_memory,
    ) -> QAResponse | None:
        final_message = (getattr(qa_response, "final_message", "") or "").strip().lower()
        answer = (getattr(qa_response, "answer", "") or "").strip().lower()

        blocked_prefixes = (
            "i could not find enough grounded information",
            "i could not find a sufficiently relevant grounded answer",
            "i could not find a grounded answer",
            "no grounded answer found",
            "no grounded answer could be safely composed",
        )

        failed_grounding = (
            any(answer.startswith(prefix) for prefix in blocked_prefixes)
            or any(final_message.startswith(prefix) for prefix in blocked_prefixes)
        )

        if not failed_grounding:
            return None

        for entry in reversed(list(conversation_memory or [])):
            previous_input = (entry.get("normalized_input") or "").strip().lower()
            previous_kind = (entry.get("kind") or "").strip().lower()

            if previous_input != normalized:
                continue
            if previous_kind != QNA_MODE:
                continue
            if not self._is_reusable_qa_entry_dict(entry):
                continue

            return QAResponse(
                mode=QNA_MODE,
                answer=entry.get("answer", ""),
                confidence=entry.get("confidence", LOW_CONFIDENCE),
                sources_used=entry.get("sources_used", []) or [],
                retrieved_contexts=entry.get("retrieved_contexts", []) or [],
                final_message="As I told you before, this question was already answered earlier in the conversation.",
            )

        return None

    def _is_reusable_qa_entry_dict(self, entry: dict[str, Any]) -> bool:
        answer = (entry.get("answer") or "").strip().lower()
        sources_used = entry.get("sources_used", []) or []
        retrieved_contexts = entry.get("retrieved_contexts", []) or []

        if not answer:
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
            "no grounded answer could be safely composed",
        )

        if any(answer.startswith(prefix) for prefix in blocked_prefixes):
            return False

        return True

    def _is_reusable_memory_entry(self, entry) -> bool:
        answer = (getattr(entry, "answer", "") or "").strip().lower()
        sources_used = getattr(entry, "sources_used", []) or []

        if not answer:
            return False
        if not sources_used:
            return False

        blocked_prefixes = (
            "i could not find enough grounded information",
            "i could not find a sufficiently relevant grounded answer",
            "i could not find a grounded answer",
            "no grounded answer found",
            "no grounded answer could be safely composed",
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

        allowed_previous_answers = {
            "Your message is empty.",
            "Please use English for food and nutrition queries.",
            "I can see the quantity, but the food name is missing.",
            "This looks like a food name, but I could not confidently match it.",
            "I recognized a quantity expression, but it is not written with digits.",
            "I could not confidently understand your input.",
            "The quantity must be a positive number of grams.",
            "This request may be unsafe and should not be answered as diet advice.",
            "This assistant only handles food, calories, and nutrition.",
        }

        for entry in reversed(list(conversation_memory or [])):
            previous_input = (entry.get("normalized_input") or "").strip().lower()
            previous_answer = (entry.get("answer") or "").strip()
            previous_kind = (entry.get("kind") or "").strip().lower()

            if previous_input != normalized:
                continue
            if previous_kind not in {QNA_MODE, "guard"}:
                continue
            if not previous_answer:
                continue

            if previous_answer not in allowed_previous_answers and not (
                previous_answer.startswith("I recognized '")
                and "but I still need the quantity in grams." in previous_answer
            ):
                continue

            return QAResponse(
                mode="guard",
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
                mode="guard",
                answer="Your message is empty.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Type a food query or a nutrition question in English. Example: 'apple 200g'.",
            )

        if input_class == "non_english":
            return QAResponse(
                mode="guard",
                answer="Please use English for food and nutrition queries.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Example: 'apple 200g' or 'Is avocado healthy?'",
            )

        if input_class == "quantity_only":
            return QAResponse(
                mode="guard",
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
                    mode="guard",
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
                    mode="guard",
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
                mode="guard",
                answer="This looks like a food name, but I could not confidently match it.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please type a clear English food name and quantity, for example: 'apple 200g'.",
            )

        if input_class == "quantity_not_numeric":
            return QAResponse(
                mode="guard",
                answer="I recognized a quantity expression, but it is not written with digits.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please write the amount with digits, for example: 'apple 200g' instead of 'apple two hundred grams'.",
            )

        if input_class == "invalid_quantity":
            return QAResponse(
                mode="guard",
                answer="The quantity must be a positive number of grams.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please use a valid amount, for example: 'rice 100g'.",
            )

        if input_class == "unsafe":
            return QAResponse(
                mode="guard",
                answer="This request may be unsafe and should not be answered as diet advice.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please ask a safe nutrition question or consult a qualified health professional.",
            )

        if input_class == "out_of_domain":
            return QAResponse(
                mode="guard",
                answer="This assistant only handles food, calories, and nutrition.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Try something like 'apple 200g' or 'What are good sources of protein?'",
            )

        if input_class == "gibberish":
            return QAResponse(
                mode="guard",
                answer="I could not confidently understand your input.",
                confidence=LOW_CONFIDENCE,
                sources_used=[],
                retrieved_contexts=[],
                final_message="Please write a clear food + grams query or a nutrition question, for example: 'banana 120g' or 'Is avocado healthy?'",
            )

        return QAResponse(
            mode="guard",
            answer="This assistant only handles food, calories, and nutrition.",
            confidence=LOW_CONFIDENCE,
            sources_used=[],
            retrieved_contexts=[],
            final_message="Try something like 'apple 200g' or 'What are good sources of protein?'",
        )