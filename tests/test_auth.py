"""
test_auth.py
============
Tests for authentication endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  GET  /api/v1/auth/me
"""

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login, auth_headers


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher1@test.com",
            "password": "securepass",
            "full_name": "Test Teacher",
            "role": "teacher",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "teacher1@test.com"
    assert data["role"] == "teacher"
    assert "id" in data
    # password must NOT appear in the response
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "password": "pass",
        "full_name": "Dup User",
        "role": "parent",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_role(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "badrole@test.com",
            "password": "pass",
            "full_name": "Bad Role",
            "role": "superuser",  # invalid
        },
    )
    assert resp.status_code == 400
    assert "invalid role" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@test.com",
            "password": "mypassword",
            "full_name": "Login User",
            "role": "admin",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "loginuser@test.com", "password": "mypassword"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@test.com",
            "password": "correct",
            "full_name": "Wrong PW",
            "role": "teacher",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    token = await _register_and_login(client, "me@test.com", "pass123", "Me User", "parent")
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
