import pytest



@pytest.mark.asyncio
async def test_missing_token_returns_401(client):
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_login_returns_auth_response(client, provisioned_test_employee):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "test@gmail.com",
            "password": "testuser1",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "accessToken" in data
    assert "refreshToken" in data
    assert "user" in data

    user = data["user"]

    assert "id" in user
    assert "employeeId" in user
    assert "username" in user
    assert "fullName" in user
    assert "roles" in user

@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(client, provisioned_test_employee, supabase_access_token):
    from app.core.config import settings
    from supabase import create_client
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test@gmail.com", "password": "testuser1"},
    )
    refresh_token = login_response.json()["refreshToken"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": "invalid-refresh-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_returns_204(client, provisioned_test_employee):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test@gmail.com", "password": "testuser1"},
    )
    access_token = login_response.json()["accessToken"]

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_without_token_returns_401(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401