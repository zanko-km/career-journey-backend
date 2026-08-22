from datetime import date

import pytest

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.employee import Employee, EmployeeStatus
from app.models import HrbpTeamAssignment, Team, Department

@pytest.mark.asyncio
async def test_hrbp_can_update_employee_status(
    client,
    db_session,
):
    manager = Employee(
        username="manager1",
        full_name="Team Manager",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(manager)
    await db_session.flush()

    department = Department(
        name="Engineering Department",
    )

    db_session.add(department)
    await db_session.flush()
    
    team = Team(
        name="Engineering",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()

    hrbp = Employee(
        username="hrbp1",
        full_name="HRBP User",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
        team_id=team.id,
    )

    db_session.add(employee)
    await db_session.flush()

    assignment = HrbpTeamAssignment(
        hrbp_id=hrbp.id,
        team_id=team.id,
    )

    db_session.add(assignment)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=hrbp.id,
        employee_id=hrbp.id,
        username="hrbp1",
        full_name="HRBP User",
        roles=["HRBP"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={
            "status": "INACTIVE",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_hr_manager_can_update_employee_status(
    client,
    db_session,
):
    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(employee)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="hr_manager",
        full_name="HR Manager",
        roles=["HR_MANAGER"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "INACTIVE"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == employee.id
    assert data["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_employee_cannot_update_employee_status(
    client,
    db_session,
):
    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(employee)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee1",
        full_name="Employee One",
        roles=["EMPLOYEE"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "INACTIVE"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_update_employee_status(
    client,
    db_session,
):
    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(employee)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.patch(
        f"/employees/{employee.id}/status",
        json={"status": "INACTIVE"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_status_without_token_returns_401(
    client,
):
    app.dependency_overrides.clear()

    response = await client.patch(
        "/employees/1/status",
        json={"status": "INACTIVE"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_status_for_missing_employee_returns_404(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="hr_manager",
        full_name="HR Manager",
        roles=["HR_MANAGER"],
    )

    response = await client.patch(
        "/employees/999999/status",
        json={"status": "INACTIVE"},
    )

    assert response.status_code == 404