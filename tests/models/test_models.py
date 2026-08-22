import pytest
from datetime import date
from app.models import Employee, EmployeeRole, Team, Position, Department


@pytest.mark.asyncio
async def test_employee_role_can_be_created(db_session):
    emp = Employee(username="ali", full_name="Ali", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()

    role = EmployeeRole(employee_id=emp.id, role="MANAGER")
    db_session.add(role)
    await db_session.flush()

    assert role.id is not None


@pytest.mark.asyncio
async def test_employee_can_have_manager_and_team(db_session):
    manager = Employee(
        username="manager1",
        full_name="Manager",
        join_date=date.today(),
    )

    department = Department(
        name="Engineering",
        description="Backend department",
    )

    db_session.add_all([manager, department])
    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()

    emp = Employee(
        username="ali",
        full_name="Ali",
        join_date=date.today(),
        manager_id=manager.id,
        team_id=team.id,
    )

    db_session.add(emp)
    await db_session.flush()

    assert emp.manager_id == manager.id
    assert emp.team_id == team.id