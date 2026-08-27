from datetime import date, datetime

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Department, Employee, HrbpTeamAssignment, Team
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_employee_can_create_meeting_with_direct_manager(
    client,
    db_session,
):
    manager = Employee(
        username="direct_manager",
        full_name="Direct Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="employee_upward_dm",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_dm",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [manager.id],
            "notes": "1:1 with my manager",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["employeeId"] == employee.id
    assert data["participants"][0]["employeeId"] == manager.id


@pytest.mark.asyncio
async def test_employee_can_create_meeting_with_team_manager(
    client,
    db_session,
):
    team_manager = Employee(
        username="team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )
    db_session.add(team_manager)
    await db_session.flush()

    department = Department(name="Engineering")
    db_session.add(department)
    await db_session.flush()

    team = Team(
        name="Platform Team",
        department_id=department.id,
        team_manager_id=team_manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    # Note: employee's *direct* manager is someone else; team_manager is
    # the "layer one" manager reached only through team.team_manager_id.
    direct_manager = Employee(
        username="direct_manager_2",
        full_name="Direct Manager",
        join_date=date.today(),
    )
    db_session.add(direct_manager)
    await db_session.flush()

    employee = Employee(
        username="employee_upward_tm",
        full_name="Employee",
        join_date=date.today(),
        manager_id=direct_manager.id,
        team_id=team.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_tm",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [team_manager.id],
            "notes": "meeting with team manager",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["participants"][0]["employeeId"] == team_manager.id


@pytest.mark.asyncio
async def test_employee_can_create_meeting_with_assigned_hrbp(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_upward",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    department = Department(name="People")
    db_session.add(department)
    await db_session.flush()

    manager = Employee(
        username="team_manager_hrbp",
        full_name="Team Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    team = Team(
        name="Support Team",
        department_id=department.id,
        team_manager_id=manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    db_session.add(HrbpTeamAssignment(hrbp_id=hrbp.id, team_id=team.id))

    employee = Employee(
        username="employee_upward_hrbp",
        full_name="Employee",
        join_date=date.today(),
        team_id=team.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_hrbp",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [hrbp.id],
            "notes": "meeting with HRBP",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["participants"][0]["employeeId"] == hrbp.id


@pytest.mark.asyncio
async def test_employee_can_create_meeting_with_hr_manager(
    client,
    db_session,
):
    hr_manager = Employee(
        username="hr_manager_upward",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    from app.models.employee_role import EmployeeRole

    db_session.add(
        EmployeeRole(employee_id=hr_manager.id, role="HR_MANAGER")
    )

    employee = Employee(
        username="employee_upward_hrm",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_hrm",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [hr_manager.id],
            "notes": "meeting with HR Manager",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["participants"][0]["employeeId"] == hr_manager.id


@pytest.mark.asyncio
async def test_employee_cannot_create_meeting_with_unrelated_employee(
    client,
    db_session,
):
    """Negative control: an Employee must NOT be able to organize a meeting
    with an arbitrary coworker who is not their manager, team manager,
    assigned HRBP, or the HR Manager."""

    coworker = Employee(
        username="random_coworker",
        full_name="Coworker",
        join_date=date.today(),
    )
    db_session.add(coworker)
    await db_session.flush()

    employee = Employee(
        username="employee_upward_negative",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_negative",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [coworker.id],
            "notes": "meeting with a random coworker",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_create_meeting_mixing_allowed_and_disallowed_participants(
    client,
    db_session,
):
    """If even one participant is outside the allowed upward set, the whole
    request must be rejected (participant_ids must be a full subset)."""

    manager = Employee(
        username="direct_manager_mixed",
        full_name="Direct Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    coworker = Employee(
        username="random_coworker_mixed",
        full_name="Coworker",
        join_date=date.today(),
    )
    db_session.add(coworker)
    await db_session.flush()

    employee = Employee(
        username="employee_upward_mixed",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_upward_mixed",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [manager.id, coworker.id],
            "notes": "meeting with manager and a coworker",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 403