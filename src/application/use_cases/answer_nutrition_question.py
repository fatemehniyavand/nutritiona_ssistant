import re

from src.application.dto.responses import QAResponse
from src.application.services.repeat_detector_service import RepeatDetectorService
from src.infrastructure.retrieval.qna_retriever import QnARetriever
from src.shared.constants import HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE
from src.shared.utils import normalize_food_key


class AnswerNutritionQuestion:
    def __init__(self):
        self.retriever = QnARetriever()
        self.repeat_detector_service = RepeatDetectorService()

    def run(self, text: str, history=None, conversation_memory=None):
        history = history or []
        conversation_memory = conversation_memory or []

        repeat_match = self.repeat_detector_service.find_qa_repeat(
            question_text=text,
            conversation_memory=conversation_memory,
            threshold=0.90,
        )

        if repeat_match["found"] and repeat_match["item"]:
            old_entry = repeat_match["item"]

            if self._is_reusable_qa_entry(old_entry):
                return QAResponse(
                    mode="nutrition_qa",
                    answer=old_entry.get(
                        "answer",
                        "As I told you before, I already answered this nutrition question.",
                    ),
                    confidence=old_entry.get("confidence", HIGH_CONFIDENCE),
                    sources_used=old_entry.get("sources_used", []) or [],
                    retrieved_contexts=old_entry.get("retrieved_contexts", []) or [],
                    final_message=(
                        f"As I told you before, this question was already answered earlier "
                        f"in the conversation (similarity={repeat_match['similarity']:.2f})."
                    ),
                )

        search_text = self._build_search_query(text, history)
        result = self.retriever.search(search_text)

        documents = result.get("documents", [[]])[0]
        distances = result.get("distances", [[]])[0]

        if not documents:
            return self._build_no_grounded_answer_response(
                text=text,
                reason="I could not find enough grounded information in the nutrition Q&A dataset.",
            )

        ranked_docs = self._rank_documents(search_text, documents, distances)
        filtered_docs = [item for item in ranked_docs if item["relevant"]]

        if not filtered_docs:
            fallback_docs = self._fallback_documents(search_text, documents, distances)
            if not fallback_docs:
                return self._build_no_grounded_answer_response(
                    text=text,
                    reason="I could not find a sufficiently relevant grounded answer for this nutrition question.",
                )
            filtered_docs = fallback_docs

        top_ranked = filtered_docs[:3]
        top_contexts = [item["document"] for item in top_ranked]

        if not self._is_grounded_for_query(text, top_contexts):
            return self._build_no_grounded_answer_response(
                text=text,
                reason="I could not find a grounded answer for this question in the current nutrition Q&A dataset.",
            )

        first_distance = top_ranked[0]["distance"] if top_ranked else None
        confidence = self._score_confidence(first_distance, len(top_contexts), top_ranked)

        answer = self._build_answer(text, top_contexts)

        if not answer or answer.strip().lower().startswith("no grounded answer found"):
            return self._build_no_grounded_answer_response(
                text=text,
                reason="No grounded answer could be safely composed from the retrieved contexts.",
            )

        return QAResponse(
            mode="nutrition_qa",
            answer=answer,
            confidence=confidence,
            sources_used=[f"qna_doc_{i+1}" for i in range(len(top_contexts))],
            retrieved_contexts=top_contexts,
            final_message="Answer generated from retrieved nutrition Q&A context.",
        )

    def _build_search_query(self, text: str, history) -> str:
        text = text.strip()

        if not history:
            return text

        normalized = text.lower()

        short_follow_up_markers = {
            "what about",
            "and",
            "how about",
            "is it",
            "does it",
            "can it",
            "for weight loss",
            "for muscle gain",
            "for diet",
            "is that healthy",
            "is this healthy",
        }

        is_short = len(text.split()) <= 6
        looks_like_follow_up = any(marker in normalized for marker in short_follow_up_markers)

        if not (is_short or looks_like_follow_up):
            return text

        previous_user_messages = [
            msg.get("content", "").strip()
            for msg in reversed(history)
            if msg.get("role") == "user" and msg.get("content", "").strip()
        ]

        for previous in previous_user_messages:
            if previous.lower() != normalized:
                return f"{previous} {text}"

        return text

    def _score_confidence(self, distance: float | None, relevant_count: int, ranked_items: list[dict]) -> str:
        if relevant_count == 0:
            return LOW_CONFIDENCE

        best_overlap = max((item.get("overlap_count", 0) for item in ranked_items), default=0)
        best_entity_overlap = max((item.get("entity_overlap_count", 0) for item in ranked_items), default=0)

        if distance is None:
            if best_overlap >= 2 or best_entity_overlap >= 1:
                return MEDIUM_CONFIDENCE
            return LOW_CONFIDENCE

        if best_entity_overlap >= 1 and best_overlap >= 2 and distance <= 0.55:
            return HIGH_CONFIDENCE

        if best_entity_overlap >= 1 and distance <= 0.75:
            return MEDIUM_CONFIDENCE

        if best_overlap >= 2 and distance <= 0.60:
            return MEDIUM_CONFIDENCE

        return LOW_CONFIDENCE

    def _build_answer(self, query: str, contexts: list[str]) -> str:
        if not contexts:
            return "No grounded answer found."

        query_entities = self._entity_tokens(query)
        answers = []

        for ctx in contexts:
            question = self._extract_question(ctx)
            answer = self._extract_answer(ctx)

            if not answer:
                continue

            blob = f"{question} {answer}".lower()

            if query_entities:
                if not any(token in blob for token in query_entities):
                    continue

                if not self._is_direct_enough_match(query, question, answer):
                    continue

            answers.append(answer)

        if not answers:
            return "No grounded answer found."

        unique_answers = self._deduplicate_answer_texts(answers)
        primary = unique_answers[0]

        if len(primary) > 800:
            primary = primary[:800].strip() + "..."

        return primary

    def _rank_documents(self, query: str, documents: list[str], distances: list[float]) -> list[dict]:
        query_tokens = self._meaningful_tokens(query)
        query_entities = self._entity_tokens(query)
        ranked = []

        for idx, doc in enumerate(documents):
            doc_question = self._extract_question(doc)
            doc_answer = self._extract_answer(doc)
            doc_blob = f"{doc_question} {doc_answer}".lower()

            doc_tokens = self._meaningful_tokens(doc_question)
            overlap = query_tokens.intersection(doc_tokens)

            entity_overlap = {token for token in query_entities if token in doc_blob}
            distance = distances[idx] if idx < len(distances) else None

            overlap_count = len(overlap)
            entity_overlap_count = len(entity_overlap)

            relevance_bonus = self._direct_match_bonus(query, doc_question, doc_answer)

            relevant = self._is_relevant(
                query_tokens=query_tokens,
                query_entities=query_entities,
                overlap_count=overlap_count,
                entity_overlap_count=entity_overlap_count,
                distance=distance,
                relevance_bonus=relevance_bonus,
            )

            ranked.append(
                {
                    "document": doc,
                    "distance": distance,
                    "overlap_count": overlap_count,
                    "entity_overlap_count": entity_overlap_count,
                    "relevance_bonus": relevance_bonus,
                    "relevant": relevant,
                }
            )

        ranked.sort(
            key=lambda item: (
                not item["relevant"],
                -item["relevance_bonus"],
                -item["entity_overlap_count"],
                -item["overlap_count"],
                item["distance"] if item["distance"] is not None else 999.0,
            )
        )
        return ranked

    def _is_relevant(
        self,
        query_tokens: set[str],
        query_entities: set[str],
        overlap_count: int,
        entity_overlap_count: int,
        distance: float | None,
        relevance_bonus: int,
    ) -> bool:
        token_count = len(query_tokens)
        has_entity_requirement = len(query_entities) > 0

        if relevance_bonus >= 2:
            return True

        if has_entity_requirement and entity_overlap_count == 0:
            return False

        if token_count == 0:
            return distance is not None and distance <= 0.75

        if token_count >= 3:
            if entity_overlap_count >= 1 and overlap_count >= 1:
                return True
            if overlap_count >= 2:
                return True
            return distance is not None and distance <= 0.35 and not has_entity_requirement

        if token_count == 2:
            if entity_overlap_count >= 1 and overlap_count >= 1:
                return True
            if overlap_count >= 1 and not has_entity_requirement:
                return True
            return distance is not None and distance <= 0.30 and not has_entity_requirement

        if entity_overlap_count >= 1:
            return True

        if overlap_count >= 1 and not has_entity_requirement:
            return True

        return distance is not None and distance <= 0.25 and not has_entity_requirement

    def _fallback_documents(self, query: str, documents: list[str], distances: list[float]) -> list[dict]:
        query_entities = self._entity_tokens(query)
        kept = []

        for idx, doc in enumerate(documents):
            distance = distances[idx] if idx < len(distances) else None
            question = self._extract_question(doc)
            answer = self._extract_answer(doc)
            blob = f"{question} {answer}".lower()

            if query_entities and not any(token in blob for token in query_entities):
                continue

            direct_bonus = self._direct_match_bonus(query, question, answer)
            if direct_bonus == 0:
                continue

            if distance is not None and distance <= 0.35:
                kept.append(
                    {
                        "document": doc,
                        "distance": distance,
                        "overlap_count": 0,
                        "entity_overlap_count": len([t for t in query_entities if t in blob]),
                        "relevance_bonus": direct_bonus,
                        "relevant": True,
                    }
                )

        kept.sort(
            key=lambda item: (
                -item["relevance_bonus"],
                item["distance"] if item["distance"] is not None else 999.0,
            )
        )
        return kept[:2]

    def _extract_question(self, doc: str) -> str:
        match = re.search(
            r"Question:\s*(.*?)\nAnswer:",
            doc,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()

        return doc.strip()

    def _extract_answer(self, doc: str) -> str:
        match = re.search(
            r"Answer:\s*(.*)$",
            doc,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return doc.strip()

        answer = match.group(1).strip()
        answer = re.sub(r"\s+", " ", answer).strip()
        return answer

    def _deduplicate_answer_texts(self, answers: list[str]) -> list[str]:
        unique = []
        seen = set()

        for answer in answers:
            normalized = normalize_food_key(answer)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(answer)

        return unique

    def _meaningful_tokens(self, text: str) -> set[str]:
        normalized = normalize_food_key(text)
        tokens = set(normalized.split())

        stopwords = {
            "what", "is", "are", "the", "a", "an", "for", "to", "of", "and",
            "in", "on", "does", "do", "can", "i", "my", "with", "it", "be",
            "good", "healthy", "about", "that", "this", "tell", "me",
            "some", "should", "would", "could", "have", "has", "had",
            "food", "foods", "eat", "eating", "question", "answer"
        }

        return {t for t in tokens if len(t) >= 3 and t not in stopwords}

    def _entity_tokens(self, text: str) -> set[str]:
        normalized = normalize_food_key(text)
        tokens = normalized.split()

        generic = {
            "what", "is", "are", "the", "a", "an", "for", "to", "of", "and",
            "in", "on", "does", "do", "can", "i", "my", "with", "it", "be",
            "good", "healthy", "about", "that", "this", "tell", "me",
            "some", "should", "would", "could", "have", "has", "had",
            "food", "foods", "eat", "eating", "benefits", "benefit",
            "nutrition", "nutritional", "question", "answer"
        }

        return {t for t in tokens if len(t) >= 3 and t not in generic}

    def _is_grounded_for_query(self, query: str, contexts: list[str]) -> bool:
        if not contexts:
            return False

        query_entities = self._entity_tokens(query)
        query_tokens = self._meaningful_tokens(query)

        blob = " ".join(contexts).lower()

        if query_entities:
            entity_hits = [token for token in query_entities if token in blob]
            return len(entity_hits) >= 1

        token_hits = [token for token in query_tokens if token in blob]
        return len(token_hits) >= 1

    def _is_reusable_qa_entry(self, entry: dict) -> bool:
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

    def _build_no_grounded_answer_response(self, text: str, reason: str) -> QAResponse:
        cleaned_question = (text or "").strip()
        return QAResponse(
            mode="nutrition_qa",
            answer=f"I could not find a grounded answer for '{cleaned_question}' in the current nutrition Q&A dataset.",
            confidence=LOW_CONFIDENCE,
            sources_used=[],
            retrieved_contexts=[],
            final_message=reason,
        )

    def _direct_match_bonus(self, query: str, question: str, answer: str) -> int:
        bonus = 0
        query_entities = self._entity_tokens(query)
        q_lower = question.lower()
        a_lower = answer.lower()

        if not query_entities:
            return bonus

        if any(token in q_lower for token in query_entities):
            bonus += 2

        if any(token in a_lower for token in query_entities):
            bonus += 1

        return bonus

    def _is_direct_enough_match(self, query: str, question: str, answer: str) -> bool:
        query_entities = self._entity_tokens(query)
        if not query_entities:
            return True

        q_lower = question.lower()
        a_lower = answer.lower()

        entity_in_question = any(token in q_lower for token in query_entities)
        entity_in_answer = any(token in a_lower for token in query_entities)

        if not (entity_in_question or entity_in_answer):
            return False

        normalized_query = normalize_food_key(query)
        generic_health_patterns = [
            "better health",
            "for better health",
            "healthy foods",
            "sources that should be included for better health",
            "dietary sources that should be included for better health",
        ]

        if "healthy" in normalized_query:
            normalized_question = normalize_food_key(question)
            if any(pattern in normalized_question for pattern in generic_health_patterns):
                if not entity_in_question:
                    return False

        return True