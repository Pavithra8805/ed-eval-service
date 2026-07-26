import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import GUID


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

    parent_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # relationships
    parent: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="students", foreign_keys=[parent_id]
    )
    sessions: Mapped[list["Session"]] = relationship(  # noqa: F821
        "Session", back_populates="student"
    )

    def __repr__(self) -> str:
        return f"<Student {self.full_name}>"
