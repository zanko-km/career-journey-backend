"""
Tests for closing the HR_MANAGER IDP gap on
`POST /competency-cycles/{cycle_id}/idp`, plus a bigger bug uncovered
while fixing it on `GET /competency-cycles/{cycle_id}/idp`.

POST bug (the one that was asked for):
  `require_roles` only listed EMPLOYEE/HRBP, so HR_MANAGER got a 403
  before even reaching the handler body.

GET bug (found while fixing the POST one, same file):
  The internal permission check was
  `if EMPLOYEE in current_user.roles and cycle.employee_id !=
  current_user.employee_id: raise 403`. Since every authenticated user
  always carries the base EMPLOYEE role (see app/core/current_user.py),
  this check fired for *everyone* viewing a cycle that wasn't their own --
  MANAGER, HRBP, and HR_MANAGER included -- even though `require_roles`
  on the decorator allowed all four roles. In practice, nobody but the
  cycle's own employee could ever load this endpoint. It's now replaced
  with the same scoped-access pattern used by GET .../radar-data:
  direct manager, assigned HRBP, or HR_MANAGER (unrestricted).

Also verified: an HR_MANAGER-authored IDP item is returned in the
`hrbpItems` bucket of the GET response (there's no separate bucket for
HR_MANAGER authors).
"""

from datetime import date, timedelta

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import (
    Competency,
    Department,
    Employee,
    EmployeeCompetency,
    HrbpTeamAssignment,
    Team,
)
from app.models.competency_cycle import CompetencyCycle, CompetencyCycleStatus
from app.models.user import EmployeeRoleType


async def _make_cycle_with_competency(db_session, employee):
    competency = Competency(name="Ownership")
    db_session.add(competency)
    await db_session.flush()

    db_session.add(
        EmployeeCompetency(employee_id=employee.id, competency_id=competency.id)
    )

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)
    return cycle, competency


@pytest.mark.asyncio
async def test_hr_manager_can_submit_idp_for_any_employee(
    client,
    db_session,
):
    hr_manager = Employee(
        username="idp_hr_manager",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    employee = Employee(
        username="idp_hr_manager_target",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, competency = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hr_manager.id,
        username="idp_hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "completed": True,
                    "comment": "Great growth this cycle.",
                    "task": "Lead the next project.",
                }
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data[0]["authorRole"] == "HR_MANAGER"
    assert data[0]["authorId"] == hr_manager.id


@pytest.mark.asyncio
async def test_employee_can_still_only_submit_idp_for_own_cycle(
    client,
    db_session,
):
    """Regression guard: a plain EMPLOYEE must still be blocked from
    submitting IDP items for someone else's cycle."""

    employee = Employee(
        username="idp_plain_employee",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    other_employee = Employee(
        username="idp_other_employee",
        full_name="Other Employee",
        join_date=date.today(),
    )
    db_session.add(other_employee)
    await db_session.flush()

    cycle, competency = await _make_cycle_with_competency(
        db_session, other_employee
    )

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="idp_plain_employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "completed": False,
                    "comment": "Should not be allowed.",
                }
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_hrbp_scope_check_still_applies_when_actor_is_only_hrbp(
    client,
    db_session,
):
    """Regression guard: an HRBP not assigned to the employee's team must
    still be rejected (the scope check must not accidentally get skipped
    now that HR_MANAGER bypasses it)."""

    hrbp = Employee(
        username="idp_unassigned_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="idp_unassigned_hrbp_target",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, competency = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="idp_unassigned_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "completed": False,
                    "comment": "Should not be allowed.",
                }
            ]
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /competency-cycles/{cycle_id}/idp -- the bigger bug found in passing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hr_manager_can_view_any_employees_idp(
    client,
    db_session,
):
    hr_manager = Employee(
        username="idp_get_hr_manager",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    employee = Employee(
        username="idp_get_hr_manager_target",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, _ = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hr_manager.id,
        username="idp_get_hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_direct_manager_can_view_employees_idp(
    client,
    db_session,
):
    """Before the fix, this 403'd even though `require_roles` allows
    MANAGER, because of the always-true EMPLOYEE-role check."""

    manager = Employee(
        username="idp_get_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="idp_get_manager_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, _ = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="idp_get_manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_assigned_hrbp_can_view_employees_idp(
    client,
    db_session,
):
    hrbp = Employee(
        username="idp_get_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    team_manager = Employee(
        username="idp_get_hrbp_team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )
    db_session.add(team_manager)
    await db_session.flush()

    department = Department(name="idp-get-hrbp-dept")
    db_session.add(department)
    await db_session.flush()

    team = Team(
        name="idp-get-hrbp-team",
        department_id=department.id,
        team_manager_id=team_manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    db_session.add(HrbpTeamAssignment(hrbp_id=hrbp.id, team_id=team.id))

    employee = Employee(
        username="idp_get_hrbp_target",
        full_name="Employee",
        join_date=date.today(),
        team_id=team.id,
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, _ = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="idp_get_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unrelated_manager_cannot_view_employees_idp(
    client,
    db_session,
):
    """Regression guard: MANAGER access must still be scoped to their own
    direct reports, not opened up to everyone."""

    unrelated_manager = Employee(
        username="idp_get_unrelated_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(unrelated_manager)
    await db_session.flush()

    actual_manager = Employee(
        username="idp_get_actual_manager",
        full_name="Actual Manager",
        join_date=date.today(),
    )
    db_session.add(actual_manager)
    await db_session.flush()

    employee = Employee(
        username="idp_get_unrelated_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=actual_manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, _ = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=unrelated_manager.id,
        username="idp_get_unrelated_manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employee_can_still_view_own_idp(
    client,
    db_session,
):
    """Regression guard: the employee themself must still be able to view
    their own IDP."""

    employee = Employee(
        username="idp_get_self",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, _ = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="idp_get_self",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_hr_manager_authored_item_appears_in_hrbp_items_bucket(
    client,
    db_session,
):
    hr_manager = Employee(
        username="idp_bucket_hr_manager",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    employee = Employee(
        username="idp_bucket_target",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, competency = await _make_cycle_with_competency(db_session, employee)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hr_manager.id,
        username="idp_bucket_hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "completed": True,
                    "comment": "From HR Manager.",
                }
            ]
        },
    )

    get_response = await client.get(f"/competency-cycles/{cycle.id}/idp")

    app.dependency_overrides.clear()

    assert get_response.status_code == 200
    data = get_response.json()
    assert len(data["hrbpItems"]) == 1
    assert data["hrbpItems"][0]["authorRole"] == "HR_MANAGER"
    assert data["employeeItems"] == []
