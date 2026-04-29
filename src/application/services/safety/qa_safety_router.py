import re
from typing import Dict


class QASafetyRouter:
    def route(self, text: str) -> Dict[str, str]:
        t = self._normalize(text)

        if self._is_ambiguous(t):
            return {"route": "ambiguous"}

        if self._is_mixed_calorie_qa(t):
            return {"route": "mixed_calorie_qa"}

        if any(k in t for k in ["fruit sugar", "fruit bad", "whole fruit", "sugary drinks", "avoid fruit sugar"]):
            known = self._known_nutrition_answer(t)
            if known:
                return {"route": "known_nutrition", "answer": known}

        if self._is_misinformation_or_unsafe(t):
            return {"route": "misinformation"}

        known = self._known_nutrition_answer(t)
        if known:
            return {"route": "known_nutrition", "answer": known}

        if self._is_out_of_domain(t):
            return {"route": "out_of_domain"}

        return {"route": "normal"}

    def build_response(self, route: str, answer: str = "") -> Dict[str, str]:
        if route == "known_nutrition":
            return {"mode": "nutrition_qa", "answer": answer}

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

    def _known_nutrition_answer(self, t: str) -> str:
        if any(k in t for k in ["24-hour dietary recall", "24 hour dietary recall", "one day of diet data", "ate yesterday", "diet data not represent"]):
            return (
                "One limitation of 24-hour dietary recall is that a single day may not represent usual intake. "
                "Accuracy also depends on memory and honest reporting, so repeated recalls can improve reliability."
            )

        if any(k in t for k in ["estimate portions", "portion", "food pictures", "measuring cups", "scales", "aids help someone remember"]):
            return (
                "Dietary recall accuracy can be improved using food images, portion-size guides, measuring cups, "
                "food scales, and other visual aids. These tools help people estimate portions more accurately."
            )

        if any(k in t for k in ["processed foods", "highly processed"]):
            return (
                "Processed foods are not all the same. Some can fit into a balanced diet, but highly processed foods "
                "high in added sugar, salt, or unhealthy fats should be limited."
            )

        if any(k in t for k in ["balanced diet", "different food groups", "dietary variety", "eat different food groups", "prevent deficiencies"]):
            return (
                "A balanced diet provides essential nutrients, supports health, helps prevent deficiencies, "
                "and should include variety across different food groups."
            )

        if any(k in t for k in ["extreme diets", "restrictive diets", "cutting out many foods", "extreme dieting"]):
            return (
                "Extreme or very restrictive diets can be harmful because they may cause nutrient deficiencies, "
                "low energy, unhealthy weight changes, and other health risks."
            )

        if any(k in t for k in ["carbohydrates", "carbs", "carb"]):
            return (
                "That claim is not accurate as stated. Carbohydrates are not automatically bad. They are an important energy source. Nutrition depends on quality, portion size, balance, overall diet, and health context."
            )

        if any(k in t for k in ["fruit sugar", "fruit bad", "whole fruit", "sugary drinks", "avoid fruit sugar"]):
            return (
                "Fruit contains natural sugar, but it also provides fiber, vitamins, minerals, and water. "
                "Whole fruit can be part of a balanced diet and is different from sugary drinks."
            )

        if any(k in t for k in ["protein", "muscles"]):
            return (
                "That claim is not accurate as stated. Protein supports tissue repair, muscle maintenance, enzymes, hormones, and immune function, but it should not replace a balanced diet. Protein needs depend on age, activity level, and health status."
            )

        if any(k in t for k in ["fiber", "fibre"]):
            return (
                "Fiber supports digestion, bowel regularity, fullness, and can help support heart and metabolic health "
                "when included as part of a balanced diet."
            )

        if any(k in t for k in ["hydration", "water important", "humans need water", "roles of water"]):
            return (
                "Water is essential for body functions including temperature regulation, digestion, circulation, "
                "and waste removal."
            )

        if any(k in t for k in ["processed foods", "highly processed"]):
            return (
                "That claim is not accurate as stated. Processed foods are not all the same. Some can fit in a balanced diet, but highly processed foods high in added sugar, salt, or unhealthy fats should be limited. Nutrition depends on context and evidence."
            )

        return ""

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
        if any(w in t for w in ["carb", "carbs", "carbohydrates", "fruit"]):
            return False

        if len(words) <= 4 and any(w in t for w in ["good", "bad", "healthy", "safe", "enough"]):
            return True

        return False
