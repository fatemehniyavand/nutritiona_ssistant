from datetime import date, timedelta
from typing import Iterable

from src.domain.models.meal_state import MealItem
from src.infrastructure.memory.sqlite_daily_log import SQLiteDailyLog


class DailyCalorieService:
    def __init__(self):
        self.db = SQLiteDailyLog()

    def log_items_today(self, items: Iterable[MealItem]) -> None:
        today = date.today().isoformat()

        for item in items:
            if item.calories is None:
                continue

            self.db.upsert_item(
                log_date=today,
                food=item.food,
                grams=float(item.grams),
                calories=float(item.calories),
                kcal_per_100g=item.kcal_per_100g,
            )

    def get_today_summary(self) -> dict:
        today = date.today().isoformat()
        return {
            "date": today,
            "total_calories": self.db.get_day_total(today),
            "items": self.db.get_day_items(today),
        }

    def get_yesterday_summary(self) -> dict:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        return {
            "date": yesterday,
            "total_calories": self.db.get_day_total(yesterday),
            "items": self.db.get_day_items(yesterday),
        }

    def compare_today_yesterday(self) -> dict:
        today = self.get_today_summary()
        yesterday = self.get_yesterday_summary()
        diff = round(today["total_calories"] - yesterday["total_calories"], 2)

        return {
            "today": today,
            "yesterday": yesterday,
            "difference": diff,
        }

    def get_week_summary(self, limit: int = 7) -> list[dict]:
        rows = self.db.get_last_days(limit)
        return [
            {
                "date": log_date,
                "total_calories": total,
            }
            for log_date, total in rows
        ]
