from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MealItem:
    food: str
    grams: float
    calories: Optional[float] = None
    kcal_per_100g: Optional[float] = None


@dataclass
class MealState:
    items: List[MealItem] = field(default_factory=list)
    total_calories: float = 0.0
    last_input: str = ""