"""
Evaluations API
===============
POST /evaluations/trigger  → creates a pending Evaluation row, enqueues its
                             UUID onto the Redis `eval_queue` list.
GET  /evaluations/{id}     → fetches the evaluation status + result.

RBAC: teachers, parents, and admins can trigger/view evaluations.
      Parent can only trigger for their child's sessions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.evaluation import Evaluation
from app.models.session import Session
from app.models.student import Student
from app.models.user import User, UserRole
from app.redis_client import enqueue_evaluation
from app.schemas.evaluation import EvaluationOut, EvaluationTrigger

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/trigger", response_model=EvaluationOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_evaluation(
    payload: EvaluationTrigger,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evaluation:
    # Verify session exists
    result = await db.execute(select(Session).where(Session.id == payload.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # RBAC access check
    if current_user.role == UserRole.teacher:
        if session.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your session")
    elif current_user.role == UserRole.parent:
        result_s = await db.execute(select(Student).where(Student.id == session.student_id))
        student = result_s.scalar_one_or_none()
        if not student or student.parent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your child's session")
    # admin: no restriction

    # Create a pending evaluation record
    evaluation = Evaluation(session_id=payload.session_id)
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)

    # Enqueue onto Redis for background worker
    await enqueue_evaluation(evaluation.id)

    return evaluation


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evaluation:
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # RBAC: check session ownership
    result_s = await db.execute(select(Session).where(Session.id == evaluation.session_id))
    session = result_s.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Associated session not found")

    if current_user.role == UserRole.teacher:
        if session.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == UserRole.parent:
        result_st = await db.execute(select(Student).where(Student.id == session.student_id))
        student = result_st.scalar_one_or_none()
        if not student or student.parent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return evaluation
