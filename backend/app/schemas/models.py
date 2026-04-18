from typing import Optional

from pydantic import BaseModel

class UserPreferences(BaseModel):
    skills: dict[str, str]
    learning_goals: list[str]
    time_per_week: Optional[str] = 'medium'

class TextInput(BaseModel):
    text: str

class RecommendationInput(BaseModel):
    query: str
    limit: int = 5