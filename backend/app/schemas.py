from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=2000)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    created_at: datetime
