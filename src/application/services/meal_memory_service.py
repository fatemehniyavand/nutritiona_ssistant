from src.domain.models.meal_state import MealState, MealItem


class MealMemoryService:
    def add_items(self, meal_state: MealState, new_items: list[MealItem]) -> MealState:
        meal_state.items.extend(new_items)
        meal_state.total_calories = self._compute_total(meal_state)
        return meal_state

    def remove_item(self, meal_state: MealState, food_name: str) -> MealState:
        normalized = food_name.strip().lower()
        meal_state.items = [
            item for item in meal_state.items
            if item.food.strip().lower() != normalized
        ]
        meal_state.total_calories = self._compute_total(meal_state)
        return meal_state

    def clear(self, meal_state: MealState) -> MealState:
        meal_state.items = []
        meal_state.total_calories = 0.0
        meal_state.last_input = ""
        return meal_state

    def summary(self, meal_state: MealState) -> str:
        if not meal_state.items:
            return "Your current meal is empty."

        lines = ["Current meal:"]
        for idx, item in enumerate(meal_state.items, start=1):
            cal_text = f"{item.calories} kcal" if item.calories is not None else "unknown kcal"
            lines.append(f"{idx}. {item.food} - {item.grams}g - {cal_text}")

        lines.append(f"Total: {meal_state.total_calories} kcal")
        return "\n".join(lines)

    def _compute_total(self, meal_state: MealState) -> float:
        total = 0.0
        for item in meal_state.items:
            if item.calories is not None:
                total += float(item.calories)
        return round(total, 2)