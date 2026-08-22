import pytest
from datetime import date

from app.main import app
from app.models import (
    Employee,
    Onboarding,
    OnboardingPhase,
    PhaseStatus
)
from app.core.current_user import (
    get_current_user,
    AuthenticatedUser,
)
from app.models.user import EmployeeRoleType


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
        status=PhaseStatus.IN_PROGRESS,
    )

    phase2 = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=2,
        title="Technical Training",
        start_date=date.today(),
        end_date=date.today(),
        status=PhaseStatus.PENDING,
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
    assert data[0]["status"] == "IN_PROGRESS"



@pytest.mark.asyncio
async def test_get_employee_onboarding_phases_without_auth_returns_401(
    client,
):

    response = await client.get(
        "/employees/1/onboarding/phases"
    )

    assert response.status_code == 401



@pytest.mark.asyncio
async def test_get_employee_onboarding_phases_not_found(
    client,
    db_session,
):

    employee = Employee(
        username="phase_not_found",
        full_name="Phase Not Found",
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


    response = await client.get(
        f"/employees/{employee.id}/onboarding/phases"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_employee_onboarding_phase(
    client,
    db_session,
):
    employee = Employee(
        username="phase_create_test",
        full_name="Phase Create Test",
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
        employee_id=employee.id,
        username="hr",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/phases",
        json={
            "phaseNumber": 1,
            "title": "Introduction",
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201

    data = response.json()

    assert data["phaseNumber"] == 1
    assert data["title"] == "Introduction"
    assert data["status"] == "PENDING"
    
    
@pytest.mark.asyncio
async def test_create_duplicate_onboarding_phase_returns_409(
    client,
    db_session,
):

    employee = Employee(
        username="phase_duplicate",
        full_name="Duplicate Test",
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


    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=1,
        title="Existing Phase",
        start_date=date.today(),
        end_date=date.today(),
        status=PhaseStatus.PENDING,
    )

    db_session.add(phase)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/phases",
        json={
            "phaseNumber": 1,
            "title": "New Phase",
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_create_onboarding_phase_forbidden_role(
    client,
    db_session,
):

    employee = Employee(
        username="phase_403_create",
        full_name="Forbidden Create",
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
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/phases",
        json={
            "phaseNumber": 1,
            "title": "Introduction",
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_create_onboarding_phase_without_auth_returns_401(
    client,
):

    response = await client.post(
        "/employees/1/onboarding/phases",
        json={
            "phaseNumber": 1,
            "title": "Introduction",
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_create_onboarding_phase_onboarding_not_found(
    client,
    db_session,
):

    employee = Employee(
        username="phase_no_onboarding",
        full_name="No Onboarding",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/phases",
        json={
            "phaseNumber": 1,
            "title": "Introduction",
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_create_onboarding_phase_validation_error(
    client,
):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        "/employees/1/onboarding/phases",
        json={
            "phaseNumber": 1,
            "startDate": str(date.today()),
            "endDate": str(date.today()),
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 422