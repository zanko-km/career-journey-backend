from datetime import date

import pytest

from fastapi import status

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
from app.models.onboarding_task import OnboardingTask
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_get_employee_onboarding_actions(
    client,
    db_session,
):

    employee = Employee(
        username="action_test",
        full_name="Action Test",
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
        title="Introduction",
        start_date=date.today(),
        end_date=date.today(),
        status=PhaseStatus.IN_PROGRESS,
    )

    db_session.add(phase)
    await db_session.flush()


    task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="Complete profile",
        due_date=date.today(),
        status="PENDING",
    )

    db_session.add(task)
    await db_session.flush()


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
        f"/employees/{employee.id}/onboarding/actions"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Complete profile"
    assert data[0]["phaseId"] == phase.id
    assert data[0]["status"] == "PENDING"
    
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_actions_without_auth_returns_401(
    client,
):

    response = await client.get(
        "/employees/1/onboarding/actions"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_actions_not_found(
    client,
    db_session,
):

    employee = Employee(
        username="action_not_found",
        full_name="No Action",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


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
        f"/employees/{employee.id}/onboarding/actions"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_employee_onboarding_action(
    client,
    db_session,
):
    employee = Employee(
        username="action_create",
        full_name="Action Create",
        join_date=date.today(),
    )

    creator = Employee(
        username="hr_creator",
        full_name="HR Creator",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            creator,
        ]
    )

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
        title="Introduction",
        start_date=date.today(),
        end_date=date.today(),
    )

    db_session.add(phase)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=creator.id,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "phaseId": phase.id,
            "title": "Setup laptop",
            "description": "Prepare employee laptop",
            "dueDate": str(date.today()),
            "status": "PENDING",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Setup laptop"
    assert data["phaseId"] == phase.id
    assert data["status"] == "PENDING"
    assert data["createdBy"]["id"] == creator.id
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_action_without_auth_returns_401(
    client,
):

    response = await client.post(
        "/employees/1/onboarding/actions",
        json={
            "title": "Setup laptop",
        },
    )


    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_action_forbidden_role(
    client,
    db_session,
):

    employee = Employee(
        username="action_forbidden",
        full_name="Forbidden",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "title": "Forbidden action",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_action_employee_not_found(
    client,
    db_session,
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
        "/employees/99999/onboarding/actions",
        json={
            "title": "Action",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_action_validation_error(
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
        "/employees/1/onboarding/actions",
        json={
            "description": "missing title",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422
