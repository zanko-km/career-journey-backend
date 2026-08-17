import pytest


@pytest.mark.asyncio
async def test_real_supabase_token(client, supabase_access_token):
    response = await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {supabase_access_token}"
        },
    )

    assert response.status_code == 200