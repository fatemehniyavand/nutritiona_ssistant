class CalorieInsightService:
    def build_weekly_insight(self, week_summary: list[dict]) -> dict:
        if not week_summary:
            return {
                "average": 0.0,
                "highest_day": None,
                "lowest_day": None,
                "message": "No calorie history is available yet.",
            }

        rows = sorted(week_summary, key=lambda x: x["date"])
        totals = [float(row["total_calories"]) for row in rows]
        average = round(sum(totals) / len(totals), 2)

        highest = max(rows, key=lambda x: x["total_calories"])
        lowest = min(rows, key=lambda x: x["total_calories"])
        today = rows[-1]
        today_total = float(today["total_calories"])

        if len(rows) >= 2:
            previous = rows[-2]
            diff = round(today_total - float(previous["total_calories"]), 2)

            if diff > 0:
                trend = f"Today is {diff} kcal higher than the previous logged day."
            elif diff < 0:
                trend = f"Today is {abs(diff)} kcal lower than the previous logged day."
            else:
                trend = "Today is equal to the previous logged day."
        else:
            trend = "Only one logged day is available, so trend analysis is limited."

        return {
            "average": average,
            "highest_day": highest,
            "lowest_day": lowest,
            "message": (
                f"Weekly average: {average} kcal/day. "
                f"Highest day: {highest['date']} ({highest['total_calories']} kcal). "
                f"Lowest day: {lowest['date']} ({lowest['total_calories']} kcal). "
                f"{trend}"
            ),
        }
