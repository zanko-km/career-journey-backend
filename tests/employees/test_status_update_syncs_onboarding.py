"""
Tests for the fix to Mismatch A (requirements-doc review): the requirement
doc says the HRBP is the one who records the continue/exit decision at the
end of onboarding, via what the code exposes as
`PATCH /employees/{employee_id}/status`. That endpoint used to only touch
`Employee.status`/`Employee.exit_type`, leaving the `Onboarding` record
(status/final_result) stale and inconsistent with it.

`PATCH /employees/{employee_id}/status` now also finalizes an employee's
open Onboarding (IN_PROGRESS or FINAL_DECISION_PENDING) when the HRBP
records a decision:
  - status=EXITED -> onboarding.status=EXITED, final_result=EXIT
  - status=ACTIVE while FINAL_DECISION_PENDING -> onboarding.status=COMPLETED,
    final_result=CONTINUE
An onboarding that's already finalized (COMPLETED/EXITED/CANCELLED) is left
untouched.
"""

from datetime import date

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Department, Employee, HrbpTeamAssignment, Position, Team
from app.models.onboarding import FinalResult, Onboarding, OnboardingStatus
from app.models.user import EmployeeRoleType


async def _make_hrbp_scoped_employee_with_onboarding(
    db_session,
    hrbp_username,
    employee_username,
    onboarding_status,
):
    hrbp = Employee(
        username=hrbp_username,
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    team_manager = Employee(
        username=f"tm-{employee_username}",
        full_name="Team Manager",
        join_date=date.today(),
    )
    db_session.add(team_manager)
    await db_session.flush()

    department = Department(name=f"dept-{employee_username}")
    db_session.add(department)
    await db_session.flush()

    team = Team(
        name=f"team-{employee_username}",
        department_id=department.id,
        team_manager_id=team_manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    position = Position(title=f"role-{employee_username}")
    db_session.add(position)
    await db_session.flush()

    db_session.add(HrbpTeamAssignment(hrbp_id=hrbp.id, team_id=team.id))

    employee = Employee(
        username=employee_username,
        full_name="Employee",
        join_date=date.today(),
        team_id=team.id,
        position_id=position.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=3,
        status=onboarding_status,
    )
    db_session.add(onboarding)
    await db_session.commit()

    return hrbp, employee, onboarding


def _hrbp_user(hrbp):
    return AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username=hrbp.username,
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


@pytest.mark.asyncio
async def test_exited_status_finalizes_final_decision_pending_onboarding_as_exited(
    client,
    db_session,
):
    hrbp, employee, onboarding = await _make_hrbp_scoped_employee_with_onboarding(
        db_session,
        "sync_hrbp_exit",
        "sync_employee_exit",
        OnboardingStatus.FINAL_DECISION_PENDING,
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED", "exitType": "TERMINATION"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    await db_session.refresh(onboarding)
    assert onboarding.status == OnboardingStatus.EXITED
    assert onboarding.final_result == FinalResult.EXIT


@pytest.mark.asyncio
async def test_exited_status_finalizes_in_progress_onboarding_as_exited(
    client,
    db_session,
):
    """The decision can also be recorded mid-onboarding (e.g. an early
    termination during month 1 or 2), not only at FINAL_DECISION_PENDING."""

    hrbp, employee, onboarding = await _make_hrbp_scoped_employee_with_onboarding(
        db_session,
        "sync_hrbp_early_exit",
        "sync_employee_early_exit",
        OnboardingStatus.IN_PROGRESS,
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED", "exitType": "RESIGNATION"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    await db_session.refresh(onboarding)
    assert onboarding.status == OnboardingStatus.EXITED
    assert onboarding.final_result == FinalResult.EXIT


@pytest.mark.asyncio
async def test_active_status_completes_final_decision_pending_onboarding(
    client,
    db_session,
):
    hrbp, employee, onboarding = await _make_hrbp_scoped_employee_with_onboarding(
        db_session,
        "sync_hrbp_continue",
        "sync_employee_continue",
        OnboardingStatus.FINAL_DECISION_PENDING,
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "ACTIVE"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    await db_session.refresh(onboarding)
    assert onboarding.status == OnboardingStatus.COMPLETED
    assert onboarding.final_result == FinalResult.CONTINUE


@pytest.mark.asyncio
async def test_status_update_does_not_reopen_an_already_finalized_onboarding(
    client,
    db_session,
):
    """Regression guard: an onboarding that's already COMPLETED must not be
    silently rewritten by an unrelated later status change."""

    hrbp, employee, onboarding = await _make_hrbp_scoped_employee_with_onboarding(
        db_session,
        "sync_hrbp_no_reopen",
        "sync_employee_no_reopen",
        OnboardingStatus.COMPLETED,
    )
    onboarding.final_result = FinalResult.CONTINUE
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "INACTIVE"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    await db_session.refresh(onboarding)
    assert onboarding.status == OnboardingStatus.COMPLETED
    assert onboarding.final_result == FinalResult.CONTINUE
