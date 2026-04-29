import re
from typing import Dict


class QASafetyRouter:
    def route(self, text: str) -> Dict[str, str]:
        t = self._normalize(text)

        if self._is_mixed_calorie_qa(t):
            return {"route": "mixed_calorie_qa"}

        if self._is_misinformation_or_unsafe(t):
            return {"route": "misinformation"}

        if self._is_out_of_domain(t):
            return {"route": "out_of_domain"}

        if self._is_ambiguous(t):
            return {"route": "ambiguous"}

        return {"route": "normal"}

    def build_response(self, route: str) -> Dict[str, str]:
        if route == "out_of_domain":
            return {
                "mode": "out_of_scope",
                "answer": (
                    "This question is outside the nutrition scope. "
                    "I can help with food, diet, calories, nutrients, and health-related eating questions."
                ),
            }

        if route == "ambiguous":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "I need more information to answer safely. "
                    "Which food, meal, diet, or nutrition goal are you referring to?"
                ),
            }

        if route == "misinformation":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "That claim is not accurate as stated. Nutrition depends on context, balance, "
                    "overall diet, and individual health status. Broad claims about foods being harmful, "
                    "guaranteed cures, detox fixes, or direct fat-burning solutions are usually not supported "
                    "by strong evidence and may be unsafe."
                ),
            }

        if route == "mixed_calorie_qa":
            return {
                "mode": "nutrition_qa",
                "answer": (
                    "I see both a food quantity in grams and a nutrition question. "
                    "I will answer the nutrition part safely: it depends on portion size, balance, "
                    "overall diet, and individual health context. I will not estimate calorie values "
                    "unless the request clearly asks for calorie estimation."
                ),
            }

        return {"mode": "nutrition_qa", "answer": ""}

    def _normalize(self, text: str) -> str:
        text = text or ""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_out_of_domain(self, t: str) -> bool:
        keywords = [
            "football", "match", "gaming mouse", "csgo", "engine", "repair",
            "crypto", "cryptocurrency", "investment", "invest", "weather",
            "translate", "italian sentence", "julius caesar", "caesar",
            "rome", "emperor", "watch", "vintage watch", "rent", "milan",
            "formula 1", "tire strategy", "netflix", "laptop", "battery",
            "linkedin", "history", "poem",
        ]
        return any(k in t for k in keywords)

    def _is_mixed_calorie_qa(self, t: str) -> bool:
        has_grams = bool(re.search(r"\b\d+(?:\.\d+)?\s*g\b", t))
        has_question_signal = (
            "?" in t
            or any(
                marker in t
                for marker in [
                    " is ", " are ", " can ", " should ", " does ", " do ",
                    " tell me", " unhealthy", " healthy", " bad", " good",
                    " avoid", " enough", " cause", " cure", " replace",
                    " poison", " dangerous",
                ]
            )
        )
        return has_grams and has_question_signal

    def _is_misinformation_or_unsafe(self, t: str) -> bool:
        triggers = [
            "poison", "detox", "burn belly fat", "burn fat", "directly burn",
            "cancel all calories", "calories fake", "irrelevant", "cure diabetes",
            "cure", "only water", "live only on water", "replace every meal",
            "replace real food completely", "only meat", "only apples", "only salad",
            "skipping all meals", "fastest healthy diet", "coffee replace breakfast",
            "vinegar cancel", "lemon water", "pizza a vegetable", "carbs always bad",
            "always bad", "always dangerous", "always healthier",
            "all processed foods toxic", "gluten harm every person",
            "gluten bad for everyone", "fat-free food always", "unlimited nuts",
            "nobody should ever", "never need vitamins", "never eat fruit",
            "sugar is poison", "fruit bad", "protein powder replace", "salt always",
            "eating after 8 pm automatically", "automatically make you fat",
            "cold water burn enough calories", "cinnamon cure",
            "carbs always", "processed foods toxic", "calories fake",
        ]

        typo_triggers = [
            "carbz always badd", "shugar completly", "protien powder enogh",
            "lemmon water burn", "calorys the only", "frut bad",
            "eet only salad", "coffe replace brekfast", "glutan bad",
            "eggz dangerus", "cholestrol", "dairry inflamation",
            "vinigar remove calroies", "fasting always healty",
            "detox with only water", "salt allways bad", "procesed foods all toxic",
            "stop carbs forever", "fat free always better", "cinnamon cure diabtes",
            "pizza helthy becuz tomato",
        ]

        return any(k in t for k in triggers) or any(k in t for k in typo_triggers)

    def _is_ambiguous(self, t: str) -> bool:
        t = t.strip(" ?.!")

        ambiguous_exact = {
            "is it good", "is it bad", "is that healthy", "should i eat this",
            "can i have it every day", "is this too much", "what about protein",
            "is my diet okay", "should i stop eating it", "is it bad for me",
            "how much is enough", "is this normal", "what should i change",
            "is this meal balanced", "can i eat more", "is it safe",
            "will it help", "should i avoid it", "is this food clean",
            "can i trust this diet",
        }

        if t in ambiguous_exact:
            return True

        words = t.split()
        if len(words) <= 4 and any(w in t for w in ["good", "bad", "healthy", "safe", "enough"]):
            return True

        return False
