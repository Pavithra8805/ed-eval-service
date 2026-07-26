"""
Sessions API
============
RBAC rules enforced at query level:
  - admin  → sees all sessions
  - teacher → sees only sessions where teacher_id == current_user.id
  - parent  → sees only sessions where student.parent_id == current_user.id

GET /sessions/{id} caches the response in Redis (TTL 5 min).
PUT /sessions/{id} and DELETE /sessions/{id} invalidate the cache.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.session import Session, SessionStatus
from app.models.student import Student
from app.models.user import User, UserRole
from app.redis_client import cache_session, get_cached_session, invalidate_session_cache
from app.schemas.session import SessionCreate, SessionOut, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ── helpers ──────────────────────────────────────────────────────────────────


def _session_to_dict(s: Session) -> dict:
    return {
        "id": str(s.id),
        "title": s.title,
        "description": s.description,
        "status": s.status.value if hasattr(s.status, "value") else s.status,
        "scheduled_at": str(s.scheduled_at),
        "teacher_id": str(s.teacher_id),
        "student_id": str(s.student_id),
        "created_at": str(s.created_at),
        "updated_at": str(s.updated_at),
    }


async def _assert_session_access(session: Session, current_user: User, db: AsyncSession) -> None:
    """Raise 403 if the current user is not allowed to access this session."""
    if current_user.role == UserRole.admin:
        return

    if current_user.role == UserRole.teacher:
        if session.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied: not your session")
        return

    if current_user.role == UserRole.parent:
        result = await db.execute(select(Student).where(Student.id == session.student_id))
        student = result.scalar_one_or_none()
        if not student or student.parent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied: not your child's session")
        return


# ── endpoints ────────────────────────────────────────────────────────────────


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Session:
    # Only teachers and admins can create sessions
    if current_user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(status_code=403, detail="Only teachers and admins can create sessions")

    teacher_id = current_user.id if current_user.role == UserRole.teacher else current_user.id

    session = Session(
        title=payload.title,
        description=payload.description,
        student_id=payload.student_id,
        teacher_id=teacher_id,
        scheduled_at=payload.scheduled_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Session]:
    stmt = select(Session)

    if current_user.role == UserRole.teacher:
        stmt = stmt.where(Session.teacher_id == current_user.id)
    elif current_user.role == UserRole.parent:
        # join through student to filter by parent
        stmt = stmt.join(Student, Session.student_id == Student.id).where(
            Student.parent_id == current_user.id
        )
    # admin: no filter

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionOut:
    # Try Redis cache first
    cached = await get_cached_session(session_id)
    if cached:
        # Still enforce RBAC even on cache hit
        # Re-check RBAC using a lightweight query
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await _assert_session_access(session, current_user, db)
        return SessionOut(**cached)

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await _assert_session_access(session, current_user, db)

    # Populate cache
    await cache_session(session_id, _session_to_dict(session))

    return session


@router.put("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # RBAC: teachers can only update their own sessions; parents cannot update
    if current_user.role == UserRole.parent:
        raise HTTPException(status_code=403, detail="Parents cannot update sessions")
    if current_user.role == UserRole.teacher and session.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: not your session")

    if payload.title is not None:
        session.title = payload.title
    if payload.description is not None:
        session.description = payload.description
    if payload.scheduled_at is not None:
        session.scheduled_at = payload.scheduled_at
    if payload.status is not None:
        try:
            session.status = SessionStatus(payload.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")

    await db.commit()
    await db.refresh(session)

    # Invalidate cache
    await invalidate_session_cache(session_id)

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # RBAC
    if current_user.role == UserRole.parent:
        raise HTTPException(status_code=403, detail="Parents cannot delete sessions")
    if current_user.role == UserRole.teacher and session.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: not your session")

    await db.delete(session)
    await db.commit()

    # Invalidate cache
    await invalidate_session_cache(session_id)
