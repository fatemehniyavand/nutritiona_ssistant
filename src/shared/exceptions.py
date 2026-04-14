class NutritionAssistantError(Exception):
    pass


class FoodNotFoundError(NutritionAssistantError):
    pass


class InvalidQueryError(NutritionAssistantError):
    pass