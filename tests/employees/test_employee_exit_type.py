"""
Tests for closing Gap D: HRBP must be able to record whether an exit was a
RESIGNATION or a TERMINATION when setting an employee's status to EXITED.

`PATCH /employees/{employee_id}/status` now accepts an optional `exitType`
field, required when `status` is `EXITED` (422 if missing), ignored/cleared
for any other status, and returned back in the response as `exitType`.

Note: `PATCH /employees/{employee_id}/status` is scoped via
`require_employee_scope`, so the HRBP in these tests must be assigned
(via `HrbpTeamAssignment`) to the target employee's team, exactly like
`POST /employees` and the other HRBP-scoped endpoints tested earlier.
"""

from datetime import date

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Department, Employee, HrbpTeamAssignment, Team
from app.models.user import EmployeeRoleType


async def _make_hrbp_scoped_employee(db_session, hrbp_username, employee_username):
    from app.models import Position

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

    # NOTE: EmployeeDetailOut currently requires `position` to be non-null
    # (a separate, already-flagged, out-of-scope bug) -- give the test
    # employee a Position so this test isn't blocked by that unrelated
    # issue.
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
    await db_session.commit()

    return hrbp, employee


def _hrbp_user(hrbp):
    return AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username=hrbp.username,
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


@pytest.mark.asyncio
async def test_hrbp_can_set_exited_status_with_resignation_type(
    client,
    db_session,
):
    hrbp, employee = await _make_hrbp_scoped_employee(
        db_session, "exit_type_hrbp_resign", "exit_type_employee_resign"
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED", "exitType": "RESIGNATION"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EXITED"
    assert data["exitType"] == "RESIGNATION"


@pytest.mark.asyncio
async def test_hrbp_can_set_exited_status_with_termination_type(
    client,
    db_session,
):
    hrbp, employee = await _make_hrbp_scoped_employee(
        db_session, "exit_type_hrbp_term", "exit_type_employee_term"
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED", "exitType": "TERMINATION"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["exitType"] == "TERMINATION"


@pytest.mark.asyncio
async def test_exited_status_without_exit_type_is_rejected(
    client,
    db_session,
):
    hrbp, employee = await _make_hrbp_scoped_employee(
        db_session, "exit_type_hrbp_missing", "exit_type_employee_missing"
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_exit_type_is_cleared_when_status_moves_away_from_exited(
    client,
    db_session,
):
    """If a previously-exited employee is reactivated, the old exit_type
    must not linger and be misread later."""

    hrbp, employee = await _make_hrbp_scoped_employee(
        db_session, "exit_type_hrbp_clear", "exit_type_employee_clear"
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    first = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "EXITED", "exitType": "RESIGNATION"},
    )
    assert first.status_code == 200
    assert first.json()["exitType"] == "RESIGNATION"

    second = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "ACTIVE"},
    )

    app.dependency_overrides.clear()

    assert second.status_code == 200
    assert second.json()["exitType"] is None


@pytest.mark.asyncio
async def test_active_status_does_not_require_exit_type(
    client,
    db_session,
):
    """Regression guard: normal status updates unrelated to exiting must
    still work without ever mentioning exitType."""

    hrbp, employee = await _make_hrbp_scoped_employee(
        db_session, "exit_type_hrbp_active", "exit_type_employee_active"
    )

    app.dependency_overrides[get_current_user] = lambda: _hrbp_user(hrbp)

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "INACTIVE"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"
    assert response.json()["exitType"] is None
