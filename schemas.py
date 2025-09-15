from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AudioMeta(BaseModel):
    id: int
    original_path: str
    duration: int
    uploaded_at: datetime

    class Config:
        orm_mode = True