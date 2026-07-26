"""
test_evaluations.py
===================
Tests for evaluation trigger and retrieval:

  POST /api/v1/evaluations/trigger
  GET  /api/v1/evaluations/{id}

Covers:
  * Teacher can trigger evaluation for their own session
  * Teacher cannot trigger evaluation for another teacher's session
  * Parent can trigger evaluation for their child's session
  * Evaluation is created with 'pending' status
  * Unauthenticated access is blocked
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login, auth_headers

FUTURE_TS = "2030-09-01T09:00:00Z"


# ── helpers ───────────────────────────────────────────────────────────────────


async def _setup_session(client: AsyncClient, suffix: str):
    """
    Creates teacher, parent, student, and a session.
    Returns (teacher_token, parent_token, session_id).
    """
    teacher_tok = await _register_and_login(
        client, f"t_{suffix}@eval.com", "pw", f"Teacher {suffix}", "teacher"
    )
    parent_tok = await _register_and_login(
        client, f"p_{suffix}@eval.com", "pw", f"Parent {suffix}", "parent"
    )
    parent_me = await client.get("/api/v1/auth/me", headers=auth_headers(parent_tok))
    parent_id = parent_me.json()["id"]

    student_resp = await client.post(
        "/api/v1/auth/students",
        json={"full_name": f"Student {suffix}", "grade": "6", "parent_id": parent_id},
        headers=auth_headers(teacher_tok),
    )
    assert student_resp.status_code == 201, student_resp.text
    student_id = student_resp.json()["id"]

    session_resp = await client.post(
        "/api/v1/sessions",
        json={
            "title": f"Eval Session {suffix}",
            "student_id": student_id,
            "scheduled_at": FUTURE_TS,
        },
        headers=auth_headers(teacher_tok),
    )
    assert session_resp.status_code == 201, session_resp.text
    return teacher_tok, parent_tok, session_resp.json()["id"]


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_evaluation_as_teacher(client: AsyncClient):
    teacher_tok, _, session_id = await _setup_session(client, "ev1")

    resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(teacher_tok),
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["session_id"] == session_id
    assert "id" in data


@pytest.mark.asyncio
async def test_trigger_evaluation_as_parent(client: AsyncClient):
    teacher_tok, parent_tok, session_id = await _setup_session(client, "ev2")

    resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(parent_tok),
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_teacher_cannot_trigger_other_teachers_session(client: AsyncClient):
    teacher_tok_1, _, session_id = await _setup_session(client, "ev3")
    teacher_tok_2 = await _register_and_login(
        client, "t_other@eval.com", "pw", "Other Teacher", "teacher"
    )

    resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(teacher_tok_2),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_nonexistent_session(client: AsyncClient):
    teacher_tok = await _register_and_login(
        client, "t_noex@eval.com", "pw", "No Session Teacher", "teacher"
    )
    resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": str(uuid.uuid4())},
        headers=auth_headers(teacher_tok),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_evaluation_as_teacher(client: AsyncClient):
    teacher_tok, _, session_id = await _setup_session(client, "ev4")

    trigger_resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(teacher_tok),
    )
    eval_id = trigger_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth_headers(teacher_tok))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == eval_id


@pytest.mark.asyncio
async def test_get_evaluation_unauthenticated(client: AsyncClient):
    teacher_tok, _, session_id = await _setup_session(client, "ev5")

    trigger_resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(teacher_tok),
    )
    eval_id = trigger_resp.json()["id"]

    resp = await client.get(f"/api/v1/evaluations/{eval_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_evaluation_wrong_teacher(client: AsyncClient):
    teacher_tok_1, _, session_id = await _setup_session(client, "ev6")
    teacher_tok_2 = await _register_and_login(
        client, "t_wrong@eval.com", "pw", "Wrong Teacher", "teacher"
    )

    trigger_resp = await client.post(
        "/api/v1/evaluations/trigger",
        json={"session_id": session_id},
        headers=auth_headers(teacher_tok_1),
    )
    eval_id = trigger_resp.json()["id"]

    resp = await client.get(f"/api/v1/evaluations/{eval_id}", headers=auth_headers(teacher_tok_2))
    assert resp.status_code == 403
