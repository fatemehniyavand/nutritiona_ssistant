from pydantic import BaseModel
from typing import List, Optional


# =========================================================
# Calorie Mode
# =========================================================

class FoodMatchResult(BaseModel):
    input_food: str
    matched_food: Optional[str] = None
    grams: Optional[float] = None

    kcal_per_100g: Optional[float] = None
    calories: Optional[float] = None

    confidence: str
    distance: Optional[float] = None

    status: str  # matched | rejected

    suggestions: List[str] = []

    # Explainability
    match_reason: Optional[str] = None
    match_source: Optional[str] = None
    why_rejected: Optional[str] = None


class CalorieResponse(BaseModel):
    mode: str = "calorie"

    items: List[FoodMatchResult]

    total_calories: Optional[float]
    confidence: str

    suggestions: List[str]

    # Explainability (global)
    coverage: float
    matched_items: int
    total_items: int

    final_message: str


# =========================================================
# Q&A Mode
# =========================================================

class QAResponse(BaseModel):
    mode: str = "nutrition_qa"

    answer: str
    confidence: str

    # Explainability
    sources_used: List[str] = []
    retrieved_contexts: List[str] = []

    final_message: str