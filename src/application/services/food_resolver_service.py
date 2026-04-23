import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


class FoodResolverService:
    """
    Conservative food resolver:
    1) exact canonical
    2) exact alias
    3) compact exact
    4) cleaned exact / compact
    5) limited fuzzy matching with strong lexical gates
    """

    QUERY_NOISE_WORDS = {
        "fresh", "raw", "ripe", "plain", "regular", "normal", "just",
        "some", "my", "the", "a", "an", "of", "food", "meal", "item", "items",
    }

    SAFE_DESCRIPTOR_WORDS = {
        "whole", "skimmed", "lowfat", "low-fat", "full-fat",
        "boiled", "fried", "grilled", "roasted", "baked", "steamed",
        "white", "brown", "black", "green", "red",
        "breast", "thigh", "fillet", "slice", "slices",
    }

    def __init__(self):
        self.food_db: Dict[str, float] = {}
        self.food_key_to_food_item: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}

        self._load_real_database()
        self._candidate_pool: Dict[str, str] = self._build_candidate_pool()

        self._canonical_compact_index: Dict[str, str] = {}
        self._alias_compact_index: Dict[str, str] = {}
        self._token_set_index: Dict[str, set[str]] = {}
        self._build_indexes()

    def resolve(self, food_name: str) -> dict:
        raw_food = (food_name or "").strip()
        normalized_food = self._normalize_food_key(raw_food)
        compact_food = self._compact_food_key(raw_food)

        if not normalized_food:
            return self._not_found_response()

        # 1) Exact canonical
        if normalized_food in self.food_db:
            return self._build_match_response(
                matched_food=normalized_food,
                kcal_per_100g=self.food_db[normalized_food],
                match_reason="Exact match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        # 2) Exact alias
        if normalized_food in self.aliases:
            canonical = self.aliases[normalized_food]
            return self._build_match_response(
                matched_food=canonical,
                kcal_per_100g=self.food_db[canonical],
                match_reason="Alias match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        # 3) Compact exact
        canonical_from_compact = self._canonical_compact_index.get(compact_food)
        if canonical_from_compact:
            return self._build_match_response(
                matched_food=canonical_from_compact,
                kcal_per_100g=self.food_db[canonical_from_compact],
                match_reason="Normalized text match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        canonical_from_alias_compact = self._alias_compact_index.get(compact_food)
        if canonical_from_alias_compact:
            return self._build_match_response(
                matched_food=canonical_from_alias_compact,
                kcal_per_100g=self.food_db[canonical_from_alias_compact],
                match_reason="Normalized alias match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        # 4) Clean query and retry exact/compact only
        cleaned_query = self._strip_query_noise(normalized_food)
        cleaned_compact = self._compact_food_key(cleaned_query)

        if cleaned_query and cleaned_query in self.food_db:
            return self._build_match_response(
                matched_food=cleaned_query,
                kcal_per_100g=self.food_db[cleaned_query],
                match_reason="Cleaned exact match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        if cleaned_query and cleaned_query in self.aliases:
            canonical = self.aliases[cleaned_query]
            return self._build_match_response(
                matched_food=canonical,
                kcal_per_100g=self.food_db[canonical],
                match_reason="Cleaned alias match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        canonical_from_clean_compact = self._canonical_compact_index.get(cleaned_compact)
        if canonical_from_clean_compact:
            return self._build_match_response(
                matched_food=canonical_from_clean_compact,
                kcal_per_100g=self.food_db[canonical_from_clean_compact],
                match_reason="Cleaned normalized match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        canonical_from_clean_alias_compact = self._alias_compact_index.get(cleaned_compact)
        if canonical_from_clean_alias_compact:
            return self._build_match_response(
                matched_food=canonical_from_clean_alias_compact,
                kcal_per_100g=self.food_db[canonical_from_clean_alias_compact],
                match_reason="Cleaned normalized alias match found in local calorie database.",
                match_source="local_calorie_db",
                confidence="HIGH",
            )

        # 5) Limited fuzzy match
        fuzzy_match = self._find_best_fuzzy_match(
            normalized_food=cleaned_query or normalized_food,
            compact_food=cleaned_compact or compact_food,
        )
        if fuzzy_match is not None:
            canonical, score, candidate_text = fuzzy_match

            confidence = "HIGH" if score >= 0.96 else "MEDIUM"
            return self._build_match_response(
                matched_food=canonical,
                kcal_per_100g=self.food_db[canonical],
                match_reason=(
                    f"High-similarity match found for '{candidate_text}' "
                    f"(score={score:.2f})."
                ),
                match_source="local_calorie_db",
                confidence=confidence,
            )

        return self._not_found_response(suggestions=self.suggest(food_name))

    def suggest(self, food_name: str, limit: int = 3) -> List[str]:
        normalized_food = self._normalize_food_key(food_name)
        compact_food = self._compact_food_key(food_name)

        if not normalized_food:
            return []

        cleaned_query = self._strip_query_noise(normalized_food)
        cleaned_compact = self._compact_food_key(cleaned_query)

        scored: List[Tuple[str, float]] = []
        seen_canonical = set()

        for candidate_text, canonical in self._candidate_pool.items():
            if canonical in seen_canonical:
                continue

            score = self._combined_similarity(
                normalized_food=cleaned_query or normalized_food,
                compact_food=cleaned_compact or compact_food,
                candidate_text=candidate_text,
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

    def _load_real_database(self) -> None:
        csv_path = self._find_calorie_csv()

        if csv_path is None:
            self._load_fallback_demo_database()
            return

        df = pd.read_csv(csv_path)

        required = {"food_item", "food_key", "calories_per_100g"}
        missing = required - set(df.columns)
        if missing:
            self._load_fallback_demo_database()
            return

        for _, row in df.iterrows():
            food_item = self._normalize_food_key(row["food_item"])
            food_key = self._normalize_food_key(str(row["food_key"]).replace("_", " "))
            kcal = float(row["calories_per_100g"])

            if not food_item:
                continue

            self.food_db[food_item] = kcal

            if food_key and food_key != food_item:
                self.food_key_to_food_item[food_key] = food_item
                self.aliases[food_key] = food_item

            compact_item = self._compact_food_key(food_item)
            if compact_item and compact_item != food_item:
                self.aliases[compact_item] = food_item

            self._register_simple_aliases(food_item)

        for alias_key, canonical in self.food_key_to_food_item.items():
            self.aliases[alias_key] = canonical

    def _find_calorie_csv(self) -> Optional[Path]:
        here = Path(__file__).resolve()

        candidates = [
            Path.cwd() / "data" / "processed" / "calories_cleaned.csv",
            here.parents[1] / "data" / "processed" / "calories_cleaned.csv",
            here.parents[2] / "data" / "processed" / "calories_cleaned.csv",
            here.parents[3] / "data" / "processed" / "calories_cleaned.csv",
            here.parents[4] / "data" / "processed" / "calories_cleaned.csv",
        ]

        for path in candidates:
            if path.exists():
                return path

        return None

    def _load_fallback_demo_database(self) -> None:
        self.food_db = {
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

        self.aliases = {
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

    def _register_simple_aliases(self, food_item: str) -> None:
        tokens = food_item.split()
        if not tokens:
            return

        compact = self._compact_food_key(food_item)
        if compact and compact != food_item:
            self.aliases.setdefault(compact, food_item)

        if len(tokens) == 1:
            token = tokens[0]
            if token.endswith("s") and len(token) > 3:
                self.aliases.setdefault(token[:-1], food_item)
            else:
                self.aliases.setdefault(token + "s", food_item)

        if len(tokens) >= 2:
            last = tokens[-1]
            if last.endswith("s") and len(last) > 3:
                variant = tokens[:-1] + [last[:-1]]
                self.aliases.setdefault(" ".join(variant), food_item)
            else:
                variant = tokens[:-1] + [last + "s"]
                self.aliases.setdefault(" ".join(variant), food_item)

            # conservative descriptor-drop alias
            filtered = [t for t in tokens if t not in self.SAFE_DESCRIPTOR_WORDS]
            if filtered and filtered != tokens and len(filtered) >= 1:
                alias_text = " ".join(filtered)
                # only keep if alias is still not too short/ambiguous
                if len(alias_text) >= 4:
                    self.aliases.setdefault(alias_text, food_item)

    def _build_candidate_pool(self) -> Dict[str, str]:
        pool: Dict[str, str] = {}

        for canonical in self.food_db.keys():
            pool[canonical] = canonical

        for alias, canonical in self.aliases.items():
            pool[alias] = canonical

        return pool

    def _build_indexes(self) -> None:
        for canonical in self.food_db.keys():
            compact = self._compact_food_key(canonical)
            if compact:
                self._canonical_compact_index.setdefault(compact, canonical)

        for alias, canonical in self.aliases.items():
            compact = self._compact_food_key(alias)
            if compact:
                self._alias_compact_index.setdefault(compact, canonical)

        all_texts = set(self.food_db.keys()) | set(self.aliases.keys())
        for text in all_texts:
            self._token_set_index[text] = set(self._meaningful_tokens(text))

    def _find_best_fuzzy_match(
        self,
        normalized_food: str,
        compact_food: str,
    ) -> Optional[Tuple[str, float, str]]:
        query_tokens = self._meaningful_tokens(normalized_food)
        if not query_tokens:
            return None

        best_candidate_text = None
        best_canonical = None
        best_score = 0.0

        for candidate_text, canonical in self._candidate_pool.items():
            candidate_tokens = self._token_set_index.get(candidate_text, set())
            if not candidate_tokens:
                continue

            score = self._combined_similarity(
                normalized_food=normalized_food,
                compact_food=compact_food,
                candidate_text=candidate_text,
            )

            if not self._passes_lexical_sanity(query_tokens, candidate_tokens, score):
                continue

            if score > best_score:
                best_score = score
                best_candidate_text = candidate_text
                best_canonical = canonical

        if best_candidate_text is None or best_canonical is None:
            return None

        if not self._passes_final_acceptance_gate(
            query_tokens=query_tokens,
            candidate_tokens=self._token_set_index.get(best_candidate_text, set()),
            query=normalized_food,
            candidate=best_candidate_text,
            score=best_score,
        ):
            return None

        return best_canonical, best_score, best_candidate_text

    def _passes_lexical_sanity(
        self,
        query_tokens: List[str],
        candidate_tokens: set[str],
        score: float,
    ) -> bool:
        if not query_tokens or not candidate_tokens:
            return False

        overlap = set(query_tokens) & candidate_tokens

        if len(query_tokens) == 1:
            q = query_tokens[0]

            if q in candidate_tokens:
                return True

            if len(candidate_tokens) == 1:
                c = list(candidate_tokens)[0]
                if len(q) >= 3 and len(c) >= 3 and q[:3] == c[:3]:
                    return score >= 0.88
                return score >= 0.93

            return False

        # multi-token queries must have real overlap
        if len(overlap) >= 2:
            return score >= 0.82

        if len(overlap) == 1:
            return score >= 0.95

        return False

    def _passes_final_acceptance_gate(
        self,
        query_tokens: List[str],
        candidate_tokens: set[str],
        query: str,
        candidate: str,
        score: float,
    ) -> bool:
        if not query_tokens or not candidate_tokens:
            return False

        overlap = set(query_tokens) & candidate_tokens

        if len(query_tokens) == 1:
            q = query_tokens[0]

            if q in candidate_tokens:
                return True

            if len(candidate_tokens) == 1:
                c = list(candidate_tokens)[0]
                if len(q) >= 3 and len(c) >= 3 and q[:3] == c[:3]:
                    return score >= 0.90
                return score >= 0.95

            return False

        primary_query_token = max(query_tokens, key=len)

        if primary_query_token not in candidate_tokens and score < 0.97:
            return False

        if len(overlap) >= 2:
            return score >= 0.84

        # one-token overlap for multi-word queries is too risky unless nearly exact
        if len(overlap) == 1:
            return score >= 0.97

        return False

    def _meaningful_tokens(self, text: str) -> List[str]:
        tokens = self._normalize_food_key(text).split()
        return [t for t in tokens if len(t) >= 2 and t not in self.QUERY_NOISE_WORDS]

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
            "match_source": "local_calorie_db",
            "confidence": "LOW",
            "suggestions": suggestions or [],
        }

    def _normalize_food_key(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = text.replace("_", " ")
        text = re.sub(r"[^a-z\s\-]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _compact_food_key(self, text: str) -> str:
        return self._normalize_food_key(text).replace(" ", "").replace("-", "")

    def _strip_query_noise(self, text: str) -> str:
        tokens = self._normalize_food_key(text).split()
        filtered = [t for t in tokens if t not in self.QUERY_NOISE_WORDS]
        return " ".join(filtered).strip()

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()