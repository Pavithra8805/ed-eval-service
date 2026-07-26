"""
test_sessions.py
================
Tests for sessions CRUD with RBAC enforcement:

  POST   /api/v1/sessions
  GET    /api/v1/sessions
  GET    /api/v1/sessions/{id}
  PUT    /api/v1/sessions/{id}
  DELETE /api/v1/sessions/{id}

Role scenarios covered
----------------------
* Teacher can create and CRUD their own sessions
* Teacher cannot read/update/delete another teacher's session
* Parent can read their child's session but cannot create/update/delete
* Admin can do everything
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login, auth_headers

FUTURE_TS = "2030-06-15T10:00:00Z"


# ── helpers ───────────────────────────────────────────────────────────────────


async def _make_teacher(client: AsyncClient, suffix: str) -> dict:
    return await _register_and_login(
        client,
        f"teacher_{suffix}@test.com",
        "pass",
        f"Teacher {suffix}",
        "teacher",
    )


async def _make_parent(client: AsyncClient, suffix: str) -> dict:
    return await _register_and_login(
        client,
        f"parent_{suffix}@test.com",
        "pass",
        f"Parent {suffix}",
        "parent",
    )


async def _make_admin(client: AsyncClient, suffix: str) -> dict:
    return await _register_and_login(
        client,
        f"admin_{suffix}@test.com",
        "pass",
        f"Admin {suffix}",
        "admin",
    )


async def _get_user_id(client: AsyncClient, token: dict) -> str:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    return resp.json()["id"]


async def _create_student(
    client: AsyncClient, parent_id: str, creator_token: dict, suffix: str
) -> str:
    resp = await client.post(
        "/api/v1/auth/students",
        json={"full_name": f"Student {suffix}", "grade": "5", "parent_id": parent_id},
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_session(
    client: AsyncClient, teacher_token: dict, student_id: str, suffix: str = "A"
) -> dict:
    resp = await client.post(
        "/api/v1/sessions",
        json={
            "title": f"Session {suffix}",
            "description": "desc",
            "student_id": student_id,
            "scheduled_at": FUTURE_TS,
        },
        headers=auth_headers(teacher_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_teacher_can_create_session(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "s1")
    parent_tok = await _make_parent(client, "s1")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok, "s1")

    session = await _create_session(client, teacher_tok, student_id)
    assert session["title"] == "Session A"
    assert "id" in session


@pytest.mark.asyncio
async def test_parent_cannot_create_session(client: AsyncClient):
    parent_tok = await _make_parent(client, "s2")
    parent_id = await _get_user_id(client, parent_tok)
    # Need a teacher to create the student
    teacher_tok = await _make_teacher(client, "s2")
    student_id = await _create_student(client, parent_id, teacher_tok, "s2")

    resp = await client.post(
        "/api/v1/sessions",
        json={
            "title": "Parent Session",
            "student_id": student_id,
            "scheduled_at": FUTURE_TS,
        },
        headers=auth_headers(parent_tok),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_teacher_list_only_own_sessions(client: AsyncClient):
    teacher_tok_a = await _make_teacher(client, "list_a")
    teacher_tok_b = await _make_teacher(client, "list_b")
    parent_tok = await _make_parent(client, "list_p")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok_a, "list")

    # teacher_a creates a session
    await _create_session(client, teacher_tok_a, student_id, "List-A")

    # teacher_b should NOT see teacher_a's sessions
    resp_b = await client.get("/api/v1/sessions", headers=auth_headers(teacher_tok_b))
    assert resp_b.status_code == 200
    ids_b = [s["id"] for s in resp_b.json()]

    resp_a = await client.get("/api/v1/sessions", headers=auth_headers(teacher_tok_a))
    ids_a = [s["id"] for s in resp_a.json()]

    # None of teacher_b's visible sessions should appear in teacher_a's set (disjoint)
    for sid in ids_b:
        assert sid not in ids_a


@pytest.mark.asyncio
async def test_parent_sees_only_childs_session(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "par_see")
    parent_tok_1 = await _make_parent(client, "par_see_1")
    parent_tok_2 = await _make_parent(client, "par_see_2")
    parent_id_1 = await _get_user_id(client, parent_tok_1)
    parent_id_2 = await _get_user_id(client, parent_tok_2)

    student_id_1 = await _create_student(client, parent_id_1, teacher_tok, "parsee1")
    student_id_2 = await _create_student(client, parent_id_2, teacher_tok, "parsee2")

    sess1 = await _create_session(client, teacher_tok, student_id_1, "ParSee-1")
    sess2 = await _create_session(client, teacher_tok, student_id_2, "ParSee-2")

    # parent_1 should see sess1 but get 403 on sess2
    resp_ok = await client.get(
        f"/api/v1/sessions/{sess1['id']}", headers=auth_headers(parent_tok_1)
    )
    assert resp_ok.status_code == 200

    resp_deny = await client.get(
        f"/api/v1/sessions/{sess2['id']}", headers=auth_headers(parent_tok_1)
    )
    assert resp_deny.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_read_any_session(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "adm_read")
    admin_tok = await _make_admin(client, "adm_read")
    parent_tok = await _make_parent(client, "adm_read")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok, "adm_read")
    session = await _create_session(client, teacher_tok, student_id, "Adm-Read")

    resp = await client.get(f"/api/v1/sessions/{session['id']}", headers=auth_headers(admin_tok))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_teacher_cannot_update_other_teachers_session(client: AsyncClient):
    teacher_tok_a = await _make_teacher(client, "upd_a")
    teacher_tok_b = await _make_teacher(client, "upd_b")
    parent_tok = await _make_parent(client, "upd_p")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok_a, "upd")
    session = await _create_session(client, teacher_tok_a, student_id, "Upd")

    resp = await client.put(
        f"/api/v1/sessions/{session['id']}",
        json={"title": "Hacked"},
        headers=auth_headers(teacher_tok_b),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_session_success(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "upd_own")
    parent_tok = await _make_parent(client, "upd_own_p")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok, "upd_own")
    session = await _create_session(client, teacher_tok, student_id, "BeforeUpdate")

    resp = await client.put(
        f"/api/v1/sessions/{session['id']}",
        json={"title": "AfterUpdate"},
        headers=auth_headers(teacher_tok),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "AfterUpdate"


@pytest.mark.asyncio
async def test_delete_session_success(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "del_own")
    parent_tok = await _make_parent(client, "del_own_p")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok, "del_own")
    session = await _create_session(client, teacher_tok, student_id, "ToDelete")

    resp = await client.delete(
        f"/api/v1/sessions/{session['id']}", headers=auth_headers(teacher_tok)
    )
    assert resp.status_code == 204

    # Confirm it's gone
    resp2 = await client.get(f"/api/v1/sessions/{session['id']}", headers=auth_headers(teacher_tok))
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_parent_cannot_delete_session(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "del_par")
    parent_tok = await _make_parent(client, "del_par_p")
    parent_id = await _get_user_id(client, parent_tok)
    student_id = await _create_student(client, parent_id, teacher_tok, "del_par")
    session = await _create_session(client, teacher_tok, student_id, "ParCantDel")

    resp = await client.delete(
        f"/api/v1/sessions/{session['id']}", headers=auth_headers(parent_tok)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_session(client: AsyncClient):
    teacher_tok = await _make_teacher(client, "noex")
    resp = await client.get(f"/api/v1/sessions/{uuid.uuid4()}", headers=auth_headers(teacher_tok))
    assert resp.status_code == 404
