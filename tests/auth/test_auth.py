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
