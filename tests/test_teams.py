import pytest
from app.main import app
from app.core.current_user import AuthenticatedUser, get_current_user


@pytest.mark.asyncio
async def test_only_hr_manager_can_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,employee_id=1, username="ali", full_name="Ali", roles=["EMPLOYEE"]
    )
    response = await client.post("/teams", json={"name": "Backend"})
    assert response.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_hr_manager_can_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1, employee_id=1, username="ali", full_name="Ali", roles=["EMPLOYEE", "HR_MANAGER"]
    )
    response = await client.post("/teams", json={"name": "Backend"})
    assert response.status_code == 200
    app.dependency_overrides.pop(get_current_user, None)