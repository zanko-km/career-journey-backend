"""Tests that hit the real Supabase auth service.

These require valid Supabase credentials in the test environment
(.env.test) and perform a real network sign-in, unlike the rest of
the auth suite which relies on the faked Supabase admin client.
"""
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
