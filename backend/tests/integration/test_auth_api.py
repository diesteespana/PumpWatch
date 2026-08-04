"""
Integration tests for auth endpoints.

Uses the test DB fixture from conftest.py (real Postgres, rolled back per test).
"""
import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "bob@example.com",
        "username": "bob",
        "password": "bobspassword1",
    })
    assert reg.status_code == 201
    data = reg.json()
    assert data["email"] == "bob@example.com"
    assert "hashed_password" not in data

    login = await client.post("/api/v1/auth/login", json={
        "email": "bob@example.com",
        "password": "bobspassword1",
    })
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "username": "dup1", "password": "duppassword1"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json={**payload, "username": "dup2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "carol@example.com", "username": "carol", "password": "correctpass1",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "carol@example.com", "password": "wrongpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no header


@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    await client.post("/api/v1/auth/register", json={
        "email": "dave@example.com", "username": "dave", "password": "davepass123",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "dave@example.com", "password": "davepass123",
    })
    token = login.json()["access_token"]

    me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "dave@example.com"


@pytest.mark.asyncio
async def test_refresh_issues_new_tokens(client):
    await client.post("/api/v1/auth/register", json={
        "email": "eve@example.com", "username": "eve", "password": "evepassword1",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "eve@example.com", "password": "evepassword1",
    })
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["access_token"] != login.json()["access_token"]
