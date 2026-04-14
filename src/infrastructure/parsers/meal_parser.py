import re
from typing import List
from src.domain.models.food import FoodItem
from src.shared.utils import split_meal_items


class MealParser:
    GRAM_PATTERN = re.compile(
        r"(?P<food>.*?)(?P<grams>\d+(?:\.\d+)?)\s*g\b",
        re.IGNORECASE
    )

    def parse(self, text: str) -> List[FoodItem]:
        items: List[FoodItem] = []

        for part in split_meal_items(text):
            match = self.GRAM_PATTERN.search(part)
            if match:
                food = match.group("food").strip()
                grams = float(match.group("grams"))
                if food:
                    items.append(FoodItem(name=food, grams=grams))
            else:
                items.append(FoodItem(name=part.strip(), grams=None))

        return items