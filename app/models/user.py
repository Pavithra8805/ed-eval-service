import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import GUID


class UserRole(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    parent = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.parent)

    # relationships
    students: Mapped[list["Student"]] = relationship(  # noqa: F821
        "Student", back_populates="parent", foreign_keys="Student.parent_id"
    )
    sessions_taught: Mapped[list["Session"]] = relationship(  # noqa: F821
        "Session", back_populates="teacher", foreign_keys="Session.teacher_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
