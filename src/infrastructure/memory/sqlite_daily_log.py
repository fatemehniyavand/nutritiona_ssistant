import sqlite3
from pathlib import Path
from typing import List, Tuple


DB_PATH = Path("storage/daily_logs.db")


class SQLiteDailyLog:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_logs (
                log_date TEXT PRIMARY KEY,
                total_calories REAL NOT NULL DEFAULT 0
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_log_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                food TEXT NOT NULL,
                grams REAL NOT NULL,
                calories REAL NOT NULL,
                kcal_per_100g REAL,
                UNIQUE(log_date, food),
                FOREIGN KEY(log_date) REFERENCES daily_logs(log_date)
            )
            """)

            conn.commit()

    def upsert_day_total(self, log_date: str, total_calories: float) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO daily_logs (log_date, total_calories)
            VALUES (?, ?)
            ON CONFLICT(log_date)
            DO UPDATE SET total_calories = excluded.total_calories
            """, (log_date, round(float(total_calories), 2)))
            conn.commit()

    def upsert_item(
        self,
        log_date: str,
        food: str,
        grams: float,
        calories: float,
        kcal_per_100g: float | None = None,
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO daily_log_items (log_date, food, grams, calories, kcal_per_100g)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(log_date, food)
            DO UPDATE SET
                grams = excluded.grams,
                calories = excluded.calories,
                kcal_per_100g = excluded.kcal_per_100g
            """, (
                log_date,
                food,
                round(float(grams), 2),
                round(float(calories), 2),
                float(kcal_per_100g) if kcal_per_100g is not None else None,
            ))

            total = self._compute_day_total(cur, log_date)
            cur.execute("""
            INSERT INTO daily_logs (log_date, total_calories)
            VALUES (?, ?)
            ON CONFLICT(log_date)
            DO UPDATE SET total_calories = excluded.total_calories
            """, (log_date, total))

            conn.commit()

    def get_day_total(self, log_date: str) -> float:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT total_calories FROM daily_logs WHERE log_date = ?", (log_date,))
            row = cur.fetchone()
            return float(row[0]) if row else 0.0

    def get_day_items(self, log_date: str) -> List[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT food, grams, calories, kcal_per_100g
            FROM daily_log_items
            WHERE log_date = ?
            ORDER BY id ASC
            """, (log_date,))
            rows = cur.fetchall()

        return [
            {
                "food": row[0],
                "grams": float(row[1]),
                "calories": float(row[2]),
                "kcal_per_100g": float(row[3]) if row[3] is not None else None,
            }
            for row in rows
        ]

    def get_last_days(self, limit: int = 7) -> List[Tuple[str, float]]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT log_date, total_calories
            FROM daily_logs
            ORDER BY log_date DESC
            LIMIT ?
            """, (int(limit),))
            return [(row[0], float(row[1])) for row in cur.fetchall()]

    def _compute_day_total(self, cur, log_date: str) -> float:
        cur.execute("""
        SELECT COALESCE(SUM(calories), 0)
        FROM daily_log_items
        WHERE log_date = ?
        """, (log_date,))
        row = cur.fetchone()
        return round(float(row[0] or 0.0), 2)
