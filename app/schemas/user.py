import uuid

from pydantic import BaseModel, EmailStr

# ── User Schemas ────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "parent"  # admin | teacher | parent


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Student Schemas ─────────────────────────────────────────────────────────


class StudentCreate(BaseModel):
    full_name: str
    grade: str | None = None
    parent_id: uuid.UUID


class StudentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    full_name: str
    grade: str | None
    parent_id: uuid.UUID
