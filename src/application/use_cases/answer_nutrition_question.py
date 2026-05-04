from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.application.dto.responses import QAResponse
from src.infrastructure.retrieval.qna_retriever import QnARetriever


class AnswerNutritionQuestion:
    def __init__(self):
        self.retriever = QnARetriever()

        # Tuned for your Chroma distances and short nutrition questions.
        self.high_similarity_threshold = 0.72
        self.medium_similarity_threshold = 0.56
        self.low_similarity_threshold = 0.48

        self.max_contexts = 5

    def run(self, question: str, history=None, conversation_memory=None) -> QAResponse:
        normalized_question = self._normalize_question(question)

        if not normalized_question:
            return self._fallback_response(
                answer="Your question is empty.",
                final_message="Please ask a clear nutrition question.",
            )

        if not self._looks_like_nutrition_question(normalized_question):
            return self._fallback_response(
                answer="This assistant only answers food and nutrition questions.",
                final_message="No nutrition-related intent was detected.",
            )

        results = self.retriever.search(
            normalized_question,
            n_results=self.max_contexts,
        )

        if not results:
            return self._fallback_response(
                answer="I could not find enough grounded information in the nutrition dataset.",
                final_message="No documents were retrieved from the Q&A collection.",
            )

        ranked_results = self._rerank(normalized_question, results)
        best = ranked_results[0]

        confidence = self._confidence_label(best.final_score)

        if confidence == "LOW":
            return QAResponse(
                mode="nutrition_qa",
                answer="I could not find a sufficiently relevant grounded answer in the nutrition dataset.",
                confidence="LOW",
                sources_used=self._source_ids(ranked_results),
                retrieved_contexts=self._contexts(ranked_results),
                final_message=(
                    "Retrieved results were available, but their similarity was too low "
                    "to answer safely without hallucination."
                ),
            )

        answer = self._build_natural_answer(best.answer)

        return QAResponse(
            mode="nutrition_qa",
            answer=answer,
            confidence=confidence,
            sources_used=self._source_ids(ranked_results),
            retrieved_contexts=self._contexts(ranked_results),
            final_message=(
                "Answer generated from the most relevant retrieved Q&A document. "
                f"Best score: {best.final_score:.2f}."
            ),
        )

    def _rerank(self, query: str, results):
        query_tokens = self._content_tokens(query)

        reranked = []

        for result in results:
            question_text = result.question or result.document
            answer_text = result.answer or result.document

            question_tokens = self._content_tokens(question_text)
            answer_tokens = self._content_tokens(answer_text)

            lexical_question = self._jaccard(query_tokens, question_tokens)
            lexical_answer = self._jaccard(query_tokens, answer_tokens)
            sequence_score = SequenceMatcher(
                None,
                query.lower(),
                question_text.lower(),
            ).ratio()

            final_score = (
                0.55 * result.similarity
                + 0.25 * lexical_question
                + 0.10 * lexical_answer
                + 0.10 * sequence_score
            )

            result.final_score = round(final_score, 4)
            result.lexical_question_score = round(lexical_question, 4)
            result.lexical_answer_score = round(lexical_answer, 4)
            result.sequence_score = round(sequence_score, 4)

            reranked.append(result)

        reranked.sort(key=lambda item: item.final_score, reverse=True)
        return reranked

    def _confidence_label(self, score: float) -> str:
        if score >= self.high_similarity_threshold:
            return "HIGH"

        if score >= self.medium_similarity_threshold:
            return "MEDIUM"

        if score >= self.low_similarity_threshold:
            return "LOW"

        return "LOW"

    def _build_natural_answer(self, answer: str) -> str:
        clean = self._clean_text(answer)

        if not clean:
            return "I could not find a grounded answer in the nutrition dataset."

        clean = re.sub(
            r"^(certainly|of course|yes)[.!]?\s*",
            "",
            clean,
            flags=re.IGNORECASE,
        )

        if clean:
            clean = clean[:1].upper() + clean[1:]

        return clean

    def _contexts(self, results) -> list[str]:
        contexts = []

        for idx, result in enumerate(results[: self.max_contexts], start=1):
            contexts.append(
                "\n".join(
                    [
                        f"Context {idx}",
                        f"ID: {result.document_id}",
                        f"Question: {self._clean_text(result.question)}",
                        f"Answer: {self._clean_text(result.answer)}",
                        f"Distance: {result.distance:.4f}",
                        f"Similarity: {result.similarity:.4f}",
                        f"Final score: {getattr(result, 'final_score', 0.0):.4f}",
                    ]
                )
            )

        return contexts

    def _source_ids(self, results) -> list[str]:
        return [result.document_id for result in results[: self.max_contexts]]

    def _fallback_response(self, answer: str, final_message: str) -> QAResponse:
        return QAResponse(
            mode="nutrition_qa",
            answer=answer,
            confidence="LOW",
            sources_used=[],
            retrieved_contexts=[],
            final_message=final_message,
        )

    def _looks_like_nutrition_question(self, text: str) -> bool:
        nutrition_terms = {
            "nutrition",
            "nutrient",
            "nutrients",
            "diet",
            "dietary",
            "food",
            "foods",
            "meal",
            "meals",
            "protein",
            "proteins",
            "carbohydrate",
            "carbohydrates",
            "carb",
            "carbs",
            "fat",
            "fats",
            "fiber",
            "fibre",
            "vitamin",
            "vitamins",
            "mineral",
            "minerals",
            "calorie",
            "calories",
            "kcal",
            "energy",
            "deficiency",
            "deficiencies",
            "malnutrition",
            "healthy",
            "health",
            "intake",
            "eating",
            "eat",
            "drink",
            "water",
            "milk",
            "egg",
            "eggs",
            "meat",
            "fish",
            "beans",
            "lentils",
            "fruit",
            "fruits",
            "vegetable",
            "vegetables",
            "anemia",
            "anaemia",
            "iron",
            "calcium",
            "assessment",
            "biochemical",
            "clinical",
            "anthropometric",
            "symptom",
            "symptoms",
            "source",
            "sources",
            "body",
            "weight",
            "underweight",
            "overweight",
            "wasting",
            "dietary",
            "habit",
            "habits",
        }

        tokens = set(self._content_tokens(text))

        if tokens & nutrition_terms:
            return True

        question_starters = (
            "what are good sources of",
            "what are sources of",
            "what is",
            "why is",
            "how does",
            "how can",
            "can you explain",
            "tell me about",
        )

        return any(text.startswith(starter) for starter in question_starters)

    def _normalize_question(self, question: str) -> str:
        text = (question or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" .?!")
        return text

    def _clean_text(self, text: str) -> str:
        clean = (text or "").strip()
        clean = re.sub(r"\s+", " ", clean)
        return clean

    def _content_tokens(self, text: str) -> list[str]:
        stopwords = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "and",
            "or",
            "that",
            "this",
            "these",
            "those",
            "what",
            "why",
            "how",
            "can",
            "could",
            "would",
            "should",
            "do",
            "does",
            "did",
            "some",
            "any",
            "about",
            "from",
            "into",
            "as",
            "by",
            "it",
            "its",
            "they",
            "them",
            "their",
            "person",
            "individual",
            "someone",
        }

        tokens = re.findall(r"[a-zA-Z]+", text.lower())
        return [token for token in tokens if token not in stopwords and len(token) >= 3]

    def _jaccard(self, left: list[str], right: list[str]) -> float:
        left_set = set(left)
        right_set = set(right)

        if not left_set or not right_set:
            return 0.0

        return len(left_set & right_set) / len(left_set | right_set)