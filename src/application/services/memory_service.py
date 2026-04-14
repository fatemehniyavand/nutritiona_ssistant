import re
from difflib import SequenceMatcher
from typing import List

from src.domain.models.conversation_memory import MemoryEntry, MemoryMatchResult


class MemoryService:
    def __init__(self, similarity_threshold: float = 0.82):
        self.similarity_threshold = similarity_threshold

    def normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def similarity(self, a: str, b: str) -> float:
        a_norm = self.normalize_text(a)
        b_norm = self.normalize_text(b)
        return SequenceMatcher(None, a_norm, b_norm).ratio()

    def find_similar_question(
        self,
        current_question: str,
        memory_entries: List[MemoryEntry],
        mode: str,
    ) -> MemoryMatchResult:
        best_score = 0.0
        best_entry = None

        for entry in memory_entries:
            if entry.mode != mode:
                continue

            if not self._is_reusable_memory_entry(entry):
                continue

            score = self.similarity(current_question, entry.question)

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= self.similarity_threshold:
            return MemoryMatchResult(
                found=True,
                matched_entry=best_entry,
                similarity_score=best_score,
            )

        return MemoryMatchResult(found=False)

    def build_memory_based_answer(self, matched_entry: MemoryEntry) -> str:
        return (
            "As I mentioned earlier, "
            f"{matched_entry.answer}\n\n"
            "You asked a very similar question before, so I reused the previous answer."
        )

    def _is_reusable_memory_entry(self, entry: MemoryEntry) -> bool:
        answer = (getattr(entry, "answer", "") or "").strip().lower()
        confidence = (getattr(entry, "confidence", "") or "").strip().lower()
        sources_used = getattr(entry, "sources_used", []) or []

        if not answer:
            return False

        if confidence == "low":
            return False

        if not sources_used:
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