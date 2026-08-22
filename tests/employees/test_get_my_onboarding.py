import pytest
from datetime import date

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser

from app.models.employee import Employee
from app.models.onboarding import (
    Onboarding,
    OnboardingStatus,
)
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_employee_can_get_own_onboarding(
    client,
    db_session,
):
    employee = Employee(
        username="employee_user",
        full_name="Employee User",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=1,
        status=OnboardingStatus.IN_PROGRESS,
    )

    db_session.add(onboarding)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        "/me/onboarding"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["employeeId"] == employee.id
    assert data["durationMonths"] == 3
    assert data["currentPhaseNumber"] == 1
    assert data["status"] == "IN_PROGRESS"
    assert data["id"] == onboarding.id
    assert data["startDate"] == str(date.today())
    
    
@pytest.mark.asyncio
async def test_employee_get_own_onboarding_fails_when_not_found(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        "/me/onboarding"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Onboarding not found"

    app.dependency_overrides.clear()
    
    
@pytest.mark.asyncio
async def test_get_my_onboarding_requires_auth(
    client,
):
    app.dependency_overrides.clear()

    response = await client.get(
        "/me/onboarding"
    )

    assert response.status_code == 401