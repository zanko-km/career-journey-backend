import pytest


@pytest.mark.asyncio
async def test_real_supabase_token(client, supabase_access_token, provisioned_test_employee):
    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {supabase_access_token}"
        },
    )

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_login_requires_username_and_password(client):
    response = await client.post(
        "/auth/login",
        json={},
    )

    assert response.status_code == 422