class CanonicalCalorieService:
    CALORIES_PER_100G = {
        "apple": 52.0,
        "banana": 89.0,
        "rice": 130.0,
        "grilled chicken": 165.0,
        "chicken": 165.0,
        "egg": 155.0,
        "milk": 61.0,
        "bread": 265.0,
        "pizza": 266.0,
        "oats": 389.0,
        "avocado": 160.0,
    }

    @classmethod
    def normalize_food_name(cls, food_name: str) -> str:
        text = (food_name or "").strip().lower()
        text = " ".join(text.split())

        aliases = {
            "white rice": "rice",
            "cooked rice": "rice",
            "boiled rice": "rice",
            "grilled chicken breast": "grilled chicken",
            "chicken breast": "grilled chicken",
            "whole egg": "egg",
            "eggs": "egg",
            "oat": "oats",
            "oatmeal": "oats",
            "cow milk": "milk",
        }

        return aliases.get(text, text)

    @classmethod
    def get_calories_per_100g(cls, food_name: str):
        normalized = cls.normalize_food_name(food_name)
        return cls.CALORIES_PER_100G.get(normalized)

    @classmethod
    def estimate_calories(cls, food_name: str, grams: float):
        kcal = cls.get_calories_per_100g(food_name)
        if kcal is None:
            return None
        return round((float(grams) * kcal) / 100.0, 2)
