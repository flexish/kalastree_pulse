"""
Pydantic contract for the daily reflection form.
"""

from pydantic import BaseModel, Field, field_validator

TEXT_FIELDS = (
    "reason",
    "biggest_win",
    "biggest_blocker",
    "tomorrow_priority",
    "need_help",
    "suggestions",
)


class ReflectionForm(BaseModel):
    rating: int = Field(ge=1, le=10)
    reason: str
    biggest_win: str
    biggest_blocker: str
    tomorrow_priority: str
    need_help: str
    suggestions: str

    @field_validator(*TEXT_FIELDS)
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Share at least a couple of words.")
        if len(cleaned) > 1000:
            raise ValueError("Keep this under 1000 characters.")
        return cleaned
