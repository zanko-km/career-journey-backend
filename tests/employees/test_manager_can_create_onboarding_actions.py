<<<<<<< HEAD
"""
Tests for closing Gap A: a Manager must be able to enter onboarding tasks
for their own direct report (e.g. right after the month-2 meeting).

Previously `POST /employees/{employee_id}/onboarding/actions` only allowed
HRBP/HR_MANAGER, which conflicted with the documented behaviour of
`POST /employees/{employee_id}/onboarding/check-month2-tasks-deadline`
(which notifies the HRBP specifically because the *manager* missed the
deadline to enter tasks themselves).

MANAGER is now allowed, but scoped: they may only create tasks for
employees who report directly to them (`employee.manager_id ==
current_user.employee_id`). HR_MANAGER remains unrestricted. HRBP is
scoped to their assigned teams via `HrbpTeamAssignment` (consistent with
every other HRBP-scoped endpoint in the app, e.g. `POST /employees` and
`start-review`), which is why the HRBP tests below set up a Team +
HrbpTeamAssignment rather than being able to act on an arbitrary employee.
"""

=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)
from datetime import date

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
<<<<<<< HEAD
from app.models import Department, HrbpTeamAssignment, Team
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)
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
<<<<<<< HEAD
    """A manager must not be able to assign tasks to someone who isn't
    their direct report, even though MANAGER is now an allowed role."""
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)

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
<<<<<<< HEAD
    """Regression guard: HRBP's pre-existing unrestricted access (used as
    the deadline-miss fallback path) must still work after adding MANAGER."""
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)

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

<<<<<<< HEAD
    department = Department(name="hrbp-fallback-dept")
    db_session.add(department)
    await db_session.flush()

    team = Team(
        name="hrbp-fallback-team",
        department_id=department.id,
        team_manager_id=manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    # HRBP task-creation is scoped to their assigned teams, same as the
    # other HRBP-scoped endpoints (POST /employees, start-review, IDP...).
    db_session.add(HrbpTeamAssignment(hrbp_id=hrbp.id, team_id=team.id))

=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)
    employee = Employee(
        username="hrbp_fallback_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
<<<<<<< HEAD
        team_id=team.id,
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)
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
<<<<<<< HEAD
    """Regression guard: plain EMPLOYEE role must still be rejected."""
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)

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
<<<<<<< HEAD


@pytest.mark.asyncio
async def test_hrbp_cannot_create_onboarding_action_outside_assigned_team(
    client,
    db_session,
):
    """An HRBP not assigned to the employee's team must be rejected, same
    as any other HRBP-scoped endpoint."""

    hrbp = Employee(
        username="hrbp_unassigned",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    manager = Employee(
        username="manager_for_unassigned_hrbp_test",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    department = Department(name="unassigned-hrbp-dept")
    db_session.add(department)
    await db_session.flush()

    team = Team(
        name="unassigned-hrbp-team",
        department_id=department.id,
        team_manager_id=manager.id,
    )
    db_session.add(team)
    await db_session.flush()
    # Note: no HrbpTeamAssignment is created for this HRBP.

    employee = Employee(
        username="unassigned_hrbp_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
        team_id=team.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_unassigned",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/actions",
        json={
            "title": "Should not be allowed",
            "dueDate": str(date.today()),
            "status": "PENDING",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403
=======
>>>>>>> 76eb787 (feat: manager can make second month task and can approved the meeting that manager made)
