from datetime import date

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_manager_can_create_onboarding_action_for_direct_report(
    client,
    db_session,
):
    manager = Employee(
        username="manager_task_owner",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="report_task_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=2,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=2,
        title="Month 2",
        start_date=date.today(),
        end_date=date.today(),
        status=PhaseStatus.IN_PROGRESS,
    )
    db_session.add(phase)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager_task_owner",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "phaseId": phase.id,
            "title": "Ship the onboarding project",
            "description": "First deliverable for month 2",
            "dueDate": str(date.today()),
            "status": "PENDING",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Ship the onboarding project"
    assert data["createdBy"]["id"] == manager.id


@pytest.mark.asyncio
async def test_manager_cannot_create_onboarding_action_for_non_report(
    client,
    db_session,
):

    manager = Employee(
        username="unrelated_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    other_manager = Employee(
        username="actual_manager",
        full_name="Actual Manager",
        join_date=date.today(),
    )
    db_session.add(other_manager)
    await db_session.flush()

    employee = Employee(
        username="someone_elses_report",
        full_name="Employee",
        join_date=date.today(),
        manager_id=other_manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=2,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=2,
        title="Month 2",
        start_date=date.today(),
        end_date=date.today(),
    )
    db_session.add(phase)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="unrelated_manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "phaseId": phase.id,
            "title": "Should not be allowed",
            "dueDate": str(date.today()),
            "status": "PENDING",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_hrbp_can_still_create_onboarding_action_for_any_employee(
    client,
    db_session,
):

    hrbp = Employee(
        username="hrbp_fallback",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    manager = Employee(
        username="some_other_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="hrbp_fallback_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=2,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=2,
        title="Month 2",
        start_date=date.today(),
        end_date=date.today(),
    )
    db_session.add(phase)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_fallback",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "phaseId": phase.id,
            "title": "Filled in by HRBP fallback",
            "dueDate": str(date.today()),
            "status": "PENDING",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["createdBy"]["id"] == hrbp.id


@pytest.mark.asyncio
async def test_employee_still_cannot_create_onboarding_action(
    client,
    db_session,
):

    employee = Employee(
        username="plain_employee_task",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="plain_employee_task",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "title": "Should not be allowed",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
