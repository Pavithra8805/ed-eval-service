import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str
    description: str | None = None
    student_id: uuid.UUID
    scheduled_at: datetime


class SessionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class SessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    description: str | None
    status: str
    scheduled_at: datetime
    teacher_id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
