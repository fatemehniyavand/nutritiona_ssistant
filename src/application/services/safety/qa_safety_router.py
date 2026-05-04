import re
from typing import Dict


class QASafetyRouter:
    def route(self, text: str) -> Dict[str, str]:
        t = self._normalize(text)

        if not t:
            return {"route": "ambiguous"}

        if self._is_out_of_domain(t):
            return {"route": "out_of_domain"}

        if self._is_personal_medical_advice(t):
            return {"route": "medical_safety"}

        if self._is_misinformation_or_unsafe_claim(t):
            return {"route": "misinformation"}

        if self._is_ambiguous(t):
            return {"route": "ambiguous"}

        if self._is_mixed_calorie_qa(t):
            return {"route": "mixed_calorie_qa"}

        return {"route": "normal"}

    def build_response(self, route: str, answer: str = "") -> Dict[str, str]:
        if route == "out_of_domain":
            return {
                "mode": "out_of_scope",
                "answer": (
                    "This question is outside the nutrition scope. "
                    "I can help with food, diet, calories, nutrients, nutritional assessment, "
                    "malnutrition, deficiencies, and healthy eating questions."
                ),
                "confidence": "LOW",
                "sources_used": [],
                "retrieved_contexts": [],
                "final_message": "Out-of-domain request rejected before retrieval.",
            }

        if route == "medical_safety":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "This question may require personal medical advice. I can provide general nutrition "
                    "information, but I cannot diagnose, prescribe treatment, or replace a healthcare professional. "
                    "Please consult a doctor or registered dietitian for advice tailored to your situation."
                ),
                "confidence": "LOW",
                "sources_used": [],
                "retrieved_contexts": [],
                "final_message": "Personal medical advice request blocked by safety router.",
            }

        if route == "ambiguous":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "I need more information to answer safely. "
                    "Which food, nutrient, symptom, diet, or nutrition topic are you referring to?"
                ),
                "confidence": "LOW",
                "sources_used": [],
                "retrieved_contexts": [],
                "final_message": "Ambiguous nutrition request blocked before retrieval.",
            }

        if route == "misinformation":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "That claim is not accurate as stated. Nutrition depends on evidence, context, "
                    "overall diet, health status, and portion size. I cannot support extreme claims, "
                    "detox claims, guaranteed cures, or advice to replace medical care."
                ),
                "confidence": "LOW",
                "sources_used": [],
                "retrieved_contexts": [],
                "final_message": "Unsafe or misleading nutrition claim blocked by safety router.",
            }

        if route == "mixed_calorie_qa":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "I see both a food quantity in grams and a nutrition question. "
                    "Please separate calorie estimation from the nutrition question so I can answer accurately."
                ),
                "confidence": "LOW",
                "sources_used": [],
                "retrieved_contexts": [],
                "final_message": "Mixed calorie and Q&A request blocked before retrieval.",
            }

        return {
            "mode": "nutrition_qa",
            "answer": answer or "",
            "confidence": "LOW",
            "sources_used": [],
            "retrieved_contexts": [],
            "final_message": "No safety response generated.",
        }

    def _normalize(self, text: str) -> str:
        text = text or ""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_out_of_domain(self, t: str) -> bool:
        nutrition_keywords = [
            "nutrition",
            "nutritional",
            "diet",
            "dietary",
            "food",
            "foods",
            "meal",
            "meals",
            "calorie",
            "calories",
            "nutrient",
            "nutrients",
            "protein",
            "proteins",
            "carbohydrate",
            "carbohydrates",
            "carbs",
            "fat",
            "fats",
            "fiber",
            "fibre",
            "vitamin",
            "mineral",
            "minerals",
            "iron",
            "calcium",
            "iodine",
            "zinc",
            "anemia",
            "anaemia",
            "hemoglobin",
            "haemoglobin",
            "malnutrition",
            "malnutriton",
            "undernutrition",
            "wasting",
            "stunting",
            "underweight",
            "overweight",
            "obesity",
            "deficiency",
            "deficiencies",
            "biochemical",
            "clinical assessment",
            "clinical examination",
            "dietary recall",
            "24-hour recall",
            "24 hour recall",
            "public health nutrition",
            "pem",
            "kwashiorkor",
            "marasmus",
            "sam",
            "severe acute",
            "icds",
            "anganwadi",
            "food fortification",
            "fortification",
            "pregnancy",
            "pregnant",
            "growth",
            "children",
            "child",
            "symptoms",
            "signs",
            "eyes",
            "ocular",
            "bitot",
            "retinol",
            "serum",
            "edema",
            "nutritional status",
            "bmi",
            "body mass index",
            "diabetes",
            "insulin",
            "healthy weight",
            "scurvy",
            "ascorbic",
            "folic acid",
            "folate",
            "megaloblastic",
            "healthy",
            "eat",
            "eating",
            "drink",
            "intake",
            "source",
            "sources",
        ]

        if any(k in t for k in nutrition_keywords):
            return False

        out_keywords = [
            "football",
            "match",
            "gaming mouse",
            "csgo",
            "engine",
            "repair",
            "crypto",
            "cryptocurrency",
            "investment",
            "invest",
            "weather",
            "translate",
            "italian sentence",
            "julius caesar",
            "caesar",
            "rome",
            "emperor",
            "watch",
            "vintage watch",
            "rent",
            "milan",
            "formula 1",
            "netflix",
            "laptop",
            "battery",
            "linkedin",
            "history",
            "poem",
            "neo4j",
            "database",
            "python",
            "java",
            "movie",
            "game",
        ]

        return any(k in t for k in out_keywords)

    def _is_personal_medical_advice(self, t: str) -> bool:
        patterns = [
            r"\bshould i take\b.*\b(supplement|iron|vitamin|zinc|magnesium|iodine)\b",
            r"\bhow much\b.*\b(supplement|iron|vitamin|zinc|magnesium|iodine)\b.*\b(take|daily|dose)\b",
            r"\bcan i stop\b.*\b(medicine|medication|insulin|antibiotic|treatment)\b",
            r"\bshould i stop\b.*\b(medicine|medication|insulin|antibiotic|treatment)\b",
            r"\bcan .* cure\b.*\b(diabetes|cancer|anemia|anaemia|kidney|heart)\b",
            r"\bhow do i treat\b.*\b(severe acute malnutrition|sam|anemia|anaemia|deficiency)\b",
            r"\bdiagnose me\b",
            r"\bdo i have\b.*\b(anemia|anaemia|diabetes|deficiency|malnutrition)\b",
        ]

        return any(re.search(pattern, t) for pattern in patterns)

    def _is_misinformation_or_unsafe_claim(self, t: str) -> bool:
        claim_markers = [
            "is poison",
            "are poison",
            "always bad",
            "always dangerous",
            "never need",
            "never eat",
            "cure diabetes",
            "cure cancer",
            "detox",
            "burn belly fat",
            "burn fat",
            "cancel calories",
            "calories fake",
            "replace every meal",
            "live only on water",
            "only water",
            "only salad",
            "only meat",
            "fruit bad",
            "sugar is poison",
            "gluten bad for everyone",
            "protein powder replace",
            "coffee replace breakfast",
            "lemon water burn",
            "vinegar cancel",
            "zero calories",
            "ignore nutrition science",
        ]

        return any(k in t for k in claim_markers)

    def _is_mixed_calorie_qa(self, t: str) -> bool:
        has_grams = bool(re.search(r"\b\d+(?:\.\d+)?\s*g\b", t))

        question_words = [
            "what",
            "why",
            "how",
            "can",
            "should",
            "does",
            "do",
            "is",
            "are",
            "healthy",
            "bad",
            "good",
            "dangerous",
            "safe",
            "avoid",
        ]

        has_question_signal = "?" in t or any(f" {w} " in f" {t} " for w in question_words)

        return has_grams and has_question_signal

    def _is_ambiguous(self, t: str) -> bool:
        stripped = t.strip(" ?.!")

        ambiguous_exact = {
            "is it good",
            "is it bad",
            "is that healthy",
            "is this healthy",
            "should i eat this",
            "can i have it every day",
            "is this too much",
            "is my diet okay",
            "should i stop eating it",
            "is it bad for me",
            "how much is enough",
            "is this normal",
            "what should i change",
            "is this meal balanced",
            "can i eat more",
            "is it safe",
            "will it help",
        }

        if stripped in ambiguous_exact:
            return True

        words = stripped.split()

        if len(words) <= 3 and any(w in stripped for w in ["good", "bad", "healthy", "safe", "enough"]):
            return True

        return False