import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


class FoodResolverService:
    """
    Resolves noisy food names to a canonical food in the local calorie database.

    Design goals:
    - exact and alias matches should be deterministic
    - spacing and hyphen differences should not matter
    - typo tolerance should exist, but not be reckless
    - suggestions should be meaningful and stable
    - out-of-distribution foods should be rejected more safely
    """

    def __init__(self):
        self.food_db: Dict[str, float] = {
            "apple": 52,
            "banana": 89,
            "milk": 61,
            "brown rice": 111,
            "rice": 130,
            "chicken": 165,
            "grilled chicken": 165,
            "egg": 155,
            "eggs": 155,
            "avocado": 160,
            "oats": 389,
            "bread": 265,
        }

        self.aliases: Dict[str, str] = {
            "apples": "apple",
            "bananas": "banana",
            "whole milk": "milk",
            "white rice": "rice",
            "brownrice": "brown rice",
            "grilledchicken": "grilled chicken",
            "chicken breast": "chicken",
            "chicken breasts": "chicken",
            "boiled egg": "egg",
            "boiled eggs": "eggs",
            "egg white": "egg",
            "egg whites": "eggs",
            "toast": "bread",
            "porridge oats": "oats",
        }

        self._candidate_pool: Dict[str, str] = self._build_candidate_pool()

    def resolve(self, food_name: str) -> dict:
        raw_food = (food_name or "").strip()
        normalized_food = self._normalize_food_key(raw_food)
        compact_food = self._compact_food_key(raw_food)

        if not normalized_food:
            return self._not_found_response()

        # 1) Exact canonical match
        if normalized_food in self.food_db:
            return self._build_match_response(
                matched_food=normalized_food,
                kcal_per_100g=self.food_db[normalized_food],
                match_reason="Exact match found in local calorie database.",
                match_source="local_demo_db",
                confidence="HIGH",
            )

        # 2) Exact alias match
        if normalized_food in self.aliases:
            canonical = self.aliases[normalized_food]
            return self._build_match_response(
                matched_food=canonical,
                kcal_per_100g=self.food_db[canonical],
                match_reason="Alias match found in local calorie database.",
                match_source="local_demo_db",
                confidence="HIGH",
            )

        # 3) Compact canonical match
        for candidate in self.food_db.keys():
            if compact_food == self._compact_food_key(candidate):
                return self._build_match_response(
                    matched_food=candidate,
                    kcal_per_100g=self.food_db[candidate],
                    match_reason="Normalized text match found in local calorie database.",
                    match_source="local_demo_db",
                    confidence="HIGH",
                )

        # 4) Compact alias match
        for alias, canonical in self.aliases.items():
            if compact_food == self._compact_food_key(alias):
                return self._build_match_response(
                    matched_food=canonical,
                    kcal_per_100g=self.food_db[canonical],
                    match_reason="Normalized alias match found in local calorie database.",
                    match_source="local_demo_db",
                    confidence="HIGH",
                )

        # 5) Safer fuzzy matching
        fuzzy_match = self._find_best_fuzzy_match(normalized_food, compact_food)
        if fuzzy_match is not None:
            canonical, score, candidate_text = fuzzy_match

            if score >= 0.93:
                return self._build_match_response(
                    matched_food=canonical,
                    kcal_per_100g=self.food_db[canonical],
                    match_reason=(
                        f"Very high-similarity match found for '{candidate_text}' "
                        f"(score={score:.2f})."
                    ),
                    match_source="local_demo_db",
                    confidence="HIGH",
                )

            if score >= 0.88:
                return self._build_match_response(
                    matched_food=canonical,
                    kcal_per_100g=self.food_db[canonical],
                    match_reason=(
                        f"High-similarity match found for '{candidate_text}' "
                        f"(score={score:.2f})."
                    ),
                    match_source="local_demo_db",
                    confidence="MEDIUM",
                )

        return self._not_found_response(suggestions=self.suggest(food_name))

    def suggest(self, food_name: str, limit: int = 3) -> List[str]:
        normalized_food = self._normalize_food_key(food_name)
        compact_food = self._compact_food_key(food_name)

        if not normalized_food:
            return []

        scored: List[Tuple[str, float]] = []
        seen_canonical = set()

        for candidate_text, canonical in self._candidate_pool.items():
            if canonical in seen_canonical:
                continue

            score = self._combined_similarity(
                normalized_food,
                compact_food,
                candidate_text,
            )
            scored.append((canonical, score))
            seen_canonical.add(canonical)

        scored.sort(key=lambda x: (-x[1], x[0]))

        suggestions = []
        for canonical, score in scored:
            if score < 0.45:
                continue
            suggestions.append(canonical)
            if len(suggestions) >= limit:
                break

        return suggestions

    def _build_candidate_pool(self) -> Dict[str, str]:
        pool: Dict[str, str] = {}

        for canonical in self.food_db.keys():
            pool[canonical] = canonical

        for alias, canonical in self.aliases.items():
            pool[alias] = canonical

        return pool

    def _find_best_fuzzy_match(
        self,
        normalized_food: str,
        compact_food: str,
    ) -> Optional[Tuple[str, float, str]]:
        best_candidate_text = None
        best_canonical = None
        best_score = 0.0

        for candidate_text, canonical in self._candidate_pool.items():
            score = self._combined_similarity(
                normalized_food=normalized_food,
                compact_food=compact_food,
                candidate_text=candidate_text,
            )

            if not self._passes_lexical_sanity(normalized_food, candidate_text, score):
                continue

            if score > best_score:
                best_score = score
                best_candidate_text = candidate_text
                best_canonical = canonical

        if best_candidate_text is None or best_canonical is None:
            return None

        if not self._passes_final_acceptance_gate(
            query=normalized_food,
            candidate=best_candidate_text,
            score=best_score,
        ):
            return None

        return best_canonical, best_score, best_candidate_text

    def _passes_lexical_sanity(self, query: str, candidate: str, score: float) -> bool:
        query_tokens = self._meaningful_tokens(query)
        candidate_tokens = self._meaningful_tokens(candidate)

        if not query_tokens or not candidate_tokens:
            return False

        if score >= 0.93:
            return True

        overlap = set(query_tokens) & set(candidate_tokens)
        if overlap:
            return True

        # Single-token typo tolerance
        if len(query_tokens) == 1 and len(candidate_tokens) == 1:
            q = query_tokens[0]
            c = candidate_tokens[0]

            if len(q) >= 3 and len(c) >= 3 and q[:3] == c[:3]:
                return True

            if self._similarity(q, c) >= 0.86:
                return True

        return False

    def _passes_final_acceptance_gate(self, query: str, candidate: str, score: float) -> bool:
        query_tokens = self._meaningful_tokens(query)
        candidate_tokens = self._meaningful_tokens(candidate)

        if not query_tokens or not candidate_tokens:
            return False

        overlap = set(query_tokens) & set(candidate_tokens)
        strong_overlap = {token for token in overlap if len(token) >= 4}
        primary_query_token = self._primary_token(query_tokens)

        # Critical OOD protection for multi-token queries:
        # the primary/distinctive token from the query must exist in the candidate.
        if len(query_tokens) >= 2:
            if primary_query_token is None:
                return False

            if primary_query_token not in candidate_tokens:
                return False

            if len(overlap) == 0:
                return False

            if len(strong_overlap) == 0 and score < 0.95:
                return False

        # Single-token typo tolerance remains allowed
        if len(query_tokens) == 1 and len(candidate_tokens) == 1:
            q = query_tokens[0]
            c = candidate_tokens[0]

            if len(q) >= 3 and len(c) >= 3 and q[:3] == c[:3]:
                return True

            if self._similarity(q, c) >= 0.88:
                return True

        if overlap:
            return True

        return score >= 0.95

    def _meaningful_tokens(self, text: str) -> List[str]:
        tokens = self._normalize_food_key(text).split()
        return [t for t in tokens if len(t) >= 2]

    def _primary_token(self, tokens: List[str]) -> Optional[str]:
        if not tokens:
            return None
        return max(tokens, key=len)

    def _combined_similarity(
        self,
        normalized_food: str,
        compact_food: str,
        candidate_text: str,
    ) -> float:
        candidate_normalized = self._normalize_food_key(candidate_text)
        candidate_compact = self._compact_food_key(candidate_text)

        normal_score = self._similarity(normalized_food, candidate_normalized)
        compact_score = self._similarity(compact_food, candidate_compact)
        token_score = self._token_similarity(normalized_food, candidate_normalized)

        return max(
            compact_score,
            round((0.45 * compact_score) + (0.35 * normal_score) + (0.20 * token_score), 4),
        )

    def _token_similarity(self, a: str, b: str) -> float:
        a_tokens = self._meaningful_tokens(a)
        b_tokens = self._meaningful_tokens(b)

        if not a_tokens or not b_tokens:
            return 0.0

        joined_a = " ".join(a_tokens)
        joined_b = " ".join(b_tokens)
        return self._similarity(joined_a, joined_b)

    def _build_match_response(
        self,
        matched_food: str,
        kcal_per_100g: float,
        match_reason: str,
        match_source: str,
        confidence: str,
    ) -> dict:
        return {
            "matched": True,
            "matched_food": matched_food,
            "kcal_per_100g": kcal_per_100g,
            "match_reason": match_reason,
            "match_source": match_source,
            "confidence": confidence,
            "suggestions": [],
        }

    def _not_found_response(self, suggestions: List[str] | None = None) -> dict:
        return {
            "matched": False,
            "matched_food": None,
            "kcal_per_100g": None,
            "match_reason": "Food not found in local calorie database.",
            "match_source": "local_demo_db",
            "confidence": "LOW",
            "suggestions": suggestions or [],
        }

    def _normalize_food_key(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"[^a-z\s\-]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _compact_food_key(self, text: str) -> str:
        return self._normalize_food_key(text).replace(" ", "").replace("-", "")

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()