from datetime import date, datetime, timedelta
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

    def get_today_summary(self, goal: float | None = None) -> dict:
        today = date.today().isoformat()
        return self.get_day_summary(today, goal=goal)

    def get_yesterday_summary(self, goal: float | None = None) -> dict:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        return self.get_day_summary(yesterday, goal=goal)

    def get_day_summary(self, log_date: str, goal: float | None = None) -> dict:
        total = self.db.get_day_total(log_date)

        return {
            "date": log_date,
            "day_name": self._day_name(log_date),
            "total_calories": total,
            "items": self.db.get_day_items(log_date),
            "goal": goal,
            "goal_status": self._goal_status(total, goal),
        }

    def compare_today_yesterday(self, goal: float | None = None) -> dict:
        today = self.get_today_summary(goal=goal)
        yesterday = self.get_yesterday_summary(goal=goal)
        diff = round(today["total_calories"] - yesterday["total_calories"], 2)

        return {
            "today": today,
            "yesterday": yesterday,
            "difference": diff,
            "message": self._compare_message(diff),
        }

    def get_week_summary(self, limit: int = 7, goal: float | None = None) -> list[dict]:
        today = date.today()
        days = []

        for i in range(limit - 1, -1, -1):
            current = today - timedelta(days=i)
            log_date = current.isoformat()
            total = self.db.get_day_total(log_date)

            days.append(
                {
                    "date": log_date,
                    "day_name": current.strftime("%A"),
                    "total_calories": total,
                    "goal": goal,
                    "goal_status": self._goal_status(total, goal),
                }
            )

        return days

    def build_weekly_report(self, goal: float | None = None, limit: int = 7) -> dict:
        days = self.get_week_summary(limit=limit, goal=goal)

        totals = [float(day["total_calories"]) for day in days]
        average = round(sum(totals) / len(totals), 2) if totals else 0.0

        highest_day = max(days, key=lambda x: x["total_calories"]) if days else None
        lowest_day = min(days, key=lambda x: x["total_calories"]) if days else None

        under_goal = 0
        over_goal = 0
        close_to_goal = 0

        if goal and goal > 0:
            for day in days:
                status = day["goal_status"]["status_code"]

                if status == "under":
                    under_goal += 1
                elif status == "over":
                    over_goal += 1
                elif status == "close":
                    close_to_goal += 1

        return {
            "days": days,
            "average_calories": average,
            "highest_day": highest_day,
            "lowest_day": lowest_day,
            "goal": goal,
            "under_goal_days": under_goal,
            "over_goal_days": over_goal,
            "close_to_goal_days": close_to_goal,
            "insight": self._weekly_insight(
                average=average,
                goal=goal,
                under_goal=under_goal,
                over_goal=over_goal,
                close_to_goal=close_to_goal,
                highest_day=highest_day,
                lowest_day=lowest_day,
            ),
        }

    def _goal_status(self, total: float, goal: float | None) -> dict:
        total = round(float(total or 0), 2)

        if goal is None or float(goal) <= 0:
            return {
                "goal": None,
                "difference": None,
                "progress_percent": None,
                "status_code": "no_goal",
                "status_label": "No goal set",
                "message": "No daily calorie goal is set.",
            }

        goal = round(float(goal), 2)
        difference = round(total - goal, 2)
        progress = round((total / goal) * 100, 1) if goal > 0 else 0
        tolerance = max(100, goal * 0.05)

        if abs(difference) <= tolerance:
            status_code = "close"
            status_label = "Close to goal"
            message = "You are close to your daily calorie goal."
        elif difference < 0:
            status_code = "under"
            status_label = "Under goal"
            message = f"You are {abs(difference)} kcal under your goal."
        else:
            status_code = "over"
            status_label = "Over goal"
            message = f"You are {difference} kcal over your goal."

        return {
            "goal": goal,
            "difference": difference,
            "progress_percent": progress,
            "status_code": status_code,
            "status_label": status_label,
            "message": message,
        }

    def _compare_message(self, diff: float) -> str:
        if diff > 0:
            return f"Today has {diff} kcal more than yesterday."
        if diff < 0:
            return f"Today has {abs(diff)} kcal less than yesterday."
        return "Today and yesterday have the same calorie total."

    def _weekly_insight(
        self,
        average: float,
        goal: float | None,
        under_goal: int,
        over_goal: int,
        close_to_goal: int,
        highest_day: dict | None,
        lowest_day: dict | None,
    ) -> str:
        lines = [f"Average intake: {average} kcal/day."]

        if highest_day:
            lines.append(
                f"Highest day: {highest_day['date']} ({highest_day['day_name']}) "
                f"with {highest_day['total_calories']} kcal."
            )

        if lowest_day:
            lines.append(
                f"Lowest day: {lowest_day['date']} ({lowest_day['day_name']}) "
                f"with {lowest_day['total_calories']} kcal."
            )

        if goal and goal > 0:
            goal = float(goal)

            lines.append(
                f"Goal alignment: {under_goal} under goal, "
                f"{over_goal} over goal, {close_to_goal} close to goal."
            )

            if average > goal:
                lines.append(
                    "Overall, this week is trending above your calorie goal based on average intake."
                )
            elif average < goal:
                lines.append(
                    "Overall, this week is trending below your calorie goal based on average intake."
                )
            else:
                lines.append(
                    "Overall, this week is exactly aligned with your calorie goal based on average intake."
                )
        else:
            lines.append("Set a daily goal with: set goal 2200")

        return " ".join(lines)

    def _day_name(self, log_date: str) -> str:
        try:
            return datetime.strptime(log_date, "%Y-%m-%d").strftime("%A")
        except Exception:
            return "Unknown"