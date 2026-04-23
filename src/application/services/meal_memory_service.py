from src.domain.models.meal_state import MealState, MealItem


class MealMemoryService:
    def add_items(self, meal_state: MealState, new_items: list[MealItem]) -> MealState:
        for item in new_items:
            self.add_or_update_item(meal_state, item)

        meal_state.total_calories = self._compute_total(meal_state)
        return meal_state

    def add_or_update_item(self, meal_state: MealState, new_item: MealItem) -> MealItem:
        existing = self.find_item(meal_state, new_item.food)

        if existing is None:
            meal_state.items.append(
                MealItem(
                    food=new_item.food,
                    grams=round(float(new_item.grams), 2),
                    calories=round(float(new_item.calories), 2) if new_item.calories is not None else None,
                    kcal_per_100g=new_item.kcal_per_100g,
                )
            )
            meal_state.total_calories = self._compute_total(meal_state)
            return meal_state.items[-1]

        # default behavior: REPLACE, not SUM
        existing.grams = round(float(new_item.grams), 2)
        existing.calories = round(float(new_item.calories), 2) if new_item.calories is not None else None

        if new_item.kcal_per_100g is not None:
            existing.kcal_per_100g = new_item.kcal_per_100g

        meal_state.total_calories = self._compute_total(meal_state)
        return existing

    def find_item(self, meal_state: MealState, food_name: str):
        normalized = (food_name or "").strip().lower()
        for item in meal_state.items:
            if (item.food or "").strip().lower() == normalized:
                return item
        return None

    def remove_item(self, meal_state: MealState, food_name: str) -> MealState:
        normalized = (food_name or "").strip().lower()
        meal_state.items = [
            item for item in meal_state.items
            if (item.food or "").strip().lower() != normalized
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