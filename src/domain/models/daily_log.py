from dataclasses import dataclass
from typing import List


@dataclass
class DailyLogItem:
    food: str
    grams: float
    calories: float


@dataclass
class DailyLog:
    date: str
    total_calories: float
    items: List[DailyLogItem]
