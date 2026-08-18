import pytest


@pytest.mark.asyncio
async def test_missing_token_returns_401(client):
    response = await client.get("/auth/me")

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    
