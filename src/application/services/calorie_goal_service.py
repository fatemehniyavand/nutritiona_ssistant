from pathlib import Path
import sqlite3
from datetime import date


class CalorieGoalService:
    def __init__(self, db_path="storage/daily_logs.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    day TEXT PRIMARY KEY,
                    target_calories REAL
                )
            """)

    def set_goal(self, target: float):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO goals(day, target_calories) VALUES (?, ?)",
                (today, float(target))
            )

    def get_today_goal(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT target_calories FROM goals WHERE day=?",
                (today,)
            ).fetchone()

        return float(row[0]) if row else None

    def build_progress(self, total_calories: float) -> dict:
        goal = self.get_today_goal()
        if goal is None:
            return {}

        remaining = round(goal - total_calories, 2)
        progress = round((total_calories / goal) * 100, 2) if goal > 0 else 0

        return {
            "goal": goal,
            "current": total_calories,
            "remaining": remaining,
            "progress": progress,
        }
