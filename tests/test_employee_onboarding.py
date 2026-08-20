import pytest
from datetime import date
from app.main import app
from app.models import Employee, Onboarding, DevelopmentPlan, OnboardingPhase
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_get_employee_onboarding(
    client,
    db_session,
):
    employee = Employee(
        username="onboarding_test",
        full_name="Onboarding Test",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        current_phase_number=1,
    )

    db_session.add(onboarding)
    await db_session.flush()


    plan = DevelopmentPlan(
        onboarding_id=onboarding.id,
        goals="Backend growth",
        skills="FastAPI",
        training="System Design",
        mentoring="Senior engineer",
        next_steps="Build APIs",
    )

    db_session.add(plan)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="manager",
        full_name="Manager",
        roles=["HR_MANAGER"],
    )

    response = await client.get(
        f"/employees/{employee.id}/onboarding"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    
    data = response.json()

    assert data["developmentPlan"]["goals"] == "Backend growth"
    assert data["developmentPlan"]["skills"] == "FastAPI"
    assert data["developmentPlan"]["training"] == "System Design"
    assert data["developmentPlan"]["mentoring"] == "Senior engineer"
    assert data["developmentPlan"]["nextSteps"] == "Build APIs"
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_without_auth_returns_401(
    client,
    db_session,
):
    employee = Employee(
        username="onboarding_401",
        full_name="Unauthorized User",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    response = await client.get(
        f"/employees/{employee.id}/onboarding"
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_forbidden_for_wrong_role(
    client,
    db_session,
):
    employee = Employee(
        username="onboarding_403",
        full_name="Forbidden User",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        current_phase_number=1,
    )

    db_session.add(onboarding)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=["EMPLOYEE"],
    )

    response = await client.get(
        f"/employees/{employee.id}/onboarding"
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_not_found(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )

    response = await client.get(
        "/employees/999999/onboarding"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_start_employee_onboarding(
    client,
    db_session,
):
    employee = Employee(
        username="start_onboarding",
        full_name="Start Test",
        join_date=date.today(),
    )

    buddy = Employee(
        username="buddy_test",
        full_name="Buddy Test",
        join_date=date.today(),
    )

    db_session.add_all([employee, buddy])
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR Manager",
        roles=["HR_MANAGER"],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding",
        json={
            "startDate": str(date.today()),
            "durationMonths": 3,
            "buddyId": buddy.id,
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 201

    data = response.json()

    assert data["employeeId"] == employee.id
    assert data["durationMonths"] == 3
    assert data["buddy"]["id"] == buddy.id
    
    
@pytest.mark.asyncio
async def test_start_onboarding_without_auth_returns_401(
    client,
    db_session,
):
    employee = Employee(
        username="no_auth_onboarding",
        full_name="No Auth",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    response = await client.post(
        f"/employees/{employee.id}/onboarding",
        json={
            "startDate": str(date.today()),
            "durationMonths": 3,
        },
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_start_onboarding_forbidden_for_employee_role(
    client,
    db_session,
):
    employee = Employee(
        username="employee_role_test",
        full_name="Employee Role",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=["EMPLOYEE"],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding",
        json={
            "startDate": str(date.today()),
            "durationMonths": 3,
        },
    )


    app.dependency_overrides.clear()

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_start_onboarding_employee_not_found(
    client,
    db_session,
):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )


    response = await client.post(
        "/employees/999999/onboarding",
        json={
            "startDate": str(date.today()),
            "durationMonths": 3,
        },
    )


    app.dependency_overrides.clear()

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_start_onboarding_twice_returns_409(
    client,
    db_session,
):
    employee = Employee(
        username="duplicate_onboarding",
        full_name="Duplicate",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )

    db_session.add(onboarding)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding",
        json={
            "startDate": str(date.today()),
            "durationMonths": 3,
        },
    )


    app.dependency_overrides.clear()

    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_update_employee_onboarding(
    client,
    db_session,
):
    employee = Employee(
        username="update_onboarding",
        full_name="Update Test",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=1,
    )

    db_session.add(onboarding)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )


    response = await client.patch(
        f"/employees/{employee.id}/onboarding",
        json={
            "durationMonths": 6
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert data["durationMonths"] == 6
    
    
@pytest.mark.asyncio
async def test_update_employee_onboarding_without_auth_returns_401(
    client,
    db_session,
):
    employee = Employee(
        username="update_401",
        full_name="Update Unauthorized",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=1,
    )

    db_session.add(onboarding)
    await db_session.flush()

    response = await client.patch(
        f"/employees/{employee.id}/onboarding",
        json={
            "durationMonths": 6
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_employee_onboarding_forbidden_for_wrong_role(
    client,
    db_session,
):
    employee = Employee(
        username="update_403",
        full_name="Update Forbidden",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=1,
    )

    db_session.add(onboarding)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=["EMPLOYEE"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/onboarding",
        json={
            "durationMonths": 6
        }
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_employee_onboarding_not_found(
    client,
    db_session,
):
    employee = Employee(
        username="update_not_found",
        full_name="Not Found",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/onboarding",
        json={
            "durationMonths": 6
        }
    )

    app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_employee_onboarding_updates_duration(
    client,
    db_session,
):
    employee = Employee(
        username="update_success",
        full_name="Update Success",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=1,
    )

    db_session.add(onboarding)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR",
        roles=["HR_MANAGER"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/onboarding",
        json={
            "durationMonths": 6
        }
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["durationMonths"] == 6
    
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_phases(
    client,
    db_session,
):
    employee = Employee(
        username="phase_test",
        full_name="Phase Test",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )

    db_session.add(onboarding)
    await db_session.flush()


    phase1 = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=1,
        title="Introduction",
        start_date=date.today(),
        end_date=date.today(),
    )

    phase2 = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=2,
        title="Technical Training",
        start_date=date.today(),
        end_date=date.today(),
    )


    db_session.add_all(
        [
            phase1,
            phase2,
        ]
    )

    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=["EMPLOYEE"],
    )


    response = await client.get(
        f"/employees/{employee.id}/onboarding/phases"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["phaseNumber"] == 1
    assert data[0]["title"] == "Introduction"
    
@pytest.mark.asyncio
async def test_get_onboarding_phases_without_auth_returns_401(
    client,
    db_session,
):

    employee = Employee(
        username="phase_401",
        full_name="Unauthorized",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    response = await client.get(
        f"/employees/{employee.id}/onboarding/phases"
    )


    assert response.status_code == 401
    
