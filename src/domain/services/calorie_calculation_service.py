class CalorieCalculationService:
    def calculate(self, grams: float, calories_per_100g: float) -> float:
        return round((grams / 100.0) * float(calories_per_100g), 2)