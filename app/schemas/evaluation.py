import uuid
from datetime import datetime

from pydantic import BaseModel


class EvaluationTrigger(BaseModel):
    session_id: uuid.UUID


class EvaluationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    session_id: uuid.UUID
    status: str
    score: float | None
    feedback: str | None
    created_at: datetime
    updated_at: datetime
