from pathlib import Path
import matplotlib.pyplot as plt


class CalorieChartService:
    def build_weekly_bar_chart(
        self,
        week_summary: list[dict],
        output_path: str = "storage/weekly_calories.png",
    ) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        rows = sorted(week_summary, key=lambda x: x["date"])
        if not rows:
            return ""

        dates = [row["date"] for row in rows]
        totals = [float(row["total_calories"]) for row in rows]

        plt.figure(figsize=(8, 4.5))
        plt.bar(dates, totals)
        plt.title("Weekly Calorie Summary")
        plt.xlabel("Date")
        plt.ylabel("Calories (kcal)")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(path, dpi=160)
        plt.close()

        return str(path)
