from pydantic import BaseModel
from typing import Optional


class FoodItem(BaseModel):
    name: str
    grams: Optional[float] = None