import pytest
from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from datetime import date
from app.models import Department, Employee, HrbpTeamAssignment, Position, Team


@pytest.mark.asyncio
async def test_get_employees_without_token_returns_401(client):
    response = await client.get("/employees")

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_employee_cannot_get_employees(client):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Test Employee",
        roles=["EMPLOYEE"],
    )

    response = await client.get("/employees")

    assert response.status_code == 403

    app.dependency_overrides.clear()
    
    
@pytest.mark.asyncio
async def test_manager_can_get_employees(client):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="manager",
        full_name="Test Manager",
        roles=["MANAGER"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_hrbp_can_get_employees(client):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=2,
        username="hrbp",
        full_name="Test HRBP",
        roles=["HRBP"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_hr_manager_can_get_employees(client):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=3,
        employee_id=3,
        username="hr_manager",
        full_name="Test HR Manager",
        roles=["HR_MANAGER"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    app.dependency_overrides.clear()
    
    
@pytest.mark.asyncio
async def test_manager_can_only_get_employees_in_management_scope(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee_in_scope = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        manager=manager,
    )

    employee_outside_scope = Employee(
        username="employee2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    db_session.add_all([
        manager,
        employee_in_scope,
        employee_outside_scope,
    ])
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    data = response.json()

    employee_ids = {employee["id"] for employee in data}

    assert employee_in_scope.id in employee_ids
    assert employee_outside_scope.id not in employee_ids

    app.dependency_overrides.clear()
    
    
@pytest.mark.asyncio
async def test_hrbp_can_only_get_employees_in_assigned_teams(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee
    from app.models.team import Team
    from app.models.department import Department
    from app.models.hrbp_team_assignment import HrbpTeamAssignment

    department = Department(
        name="Engineering",
        description="Engineering Department",
    )

    team_manager = Employee(
        username="team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )

    team = Team(
        name="Backend",
        department=department,
        team_manager=team_manager,
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee_in_scope = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        team=team,
    )

    employee_outside_scope = Employee(
        username="employee2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    assignment = HrbpTeamAssignment(
        hrbp=hrbp,
        team=team,
    )

    db_session.add_all([
        department,
        team,
        hrbp,
        employee_in_scope,
        employee_outside_scope,
        assignment,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    data = response.json()

    employee_ids = {employee["id"] for employee in data}

    assert employee_in_scope.id in employee_ids
    assert employee_outside_scope.id not in employee_ids
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_get_all_employees(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee

    employee1 = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
    )

    employee2 = Employee(
        username="employee2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    db_session.add_all([
        employee1,
        employee2,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="hr_manager",
        full_name="HR Manager",
        roles=["HR_MANAGER"],
    )

    response = await client.get("/employees")

    assert response.status_code == 200

    data = response.json()

    employee_ids = {employee["id"] for employee in data}

    assert employee1.id in employee_ids
    assert employee2.id in employee_ids
    
@pytest.mark.asyncio
async def test_get_employee_without_token_returns_401(client):
    response = await client.get("/employees/1")

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_manager_can_get_employee_in_management_scope(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        manager=manager,
    )

    db_session.add_all([
        manager,
        employee,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(f"/employees/{employee.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == employee.id
    assert data["fullName"] == "Employee One"
    
@pytest.mark.asyncio
async def test_manager_cannot_get_employee_outside_management_scope(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee_outside_scope = Employee(
        username="employee2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    db_session.add_all([
        manager,
        employee_outside_scope,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(
        f"/employees/{employee_outside_scope.id}"
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_hrbp_can_get_employee_in_assigned_team(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee
    from app.models.team import Team
    from app.models.department import Department
    from app.models.hrbp_team_assignment import HrbpTeamAssignment

    department = Department(
        name="Engineering",
        description="Engineering Department",
    )

    team_manager = Employee(
        username="team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )

    team = Team(
        name="Backend",
        department=department,
        team_manager=team_manager,
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee1",
        full_name="Employee One",
        join_date=date.today(),
        team=team,
    )

    assignment = HrbpTeamAssignment(
        hrbp=hrbp,
        team=team,
    )

    db_session.add_all([
        department,
        team,
        hrbp,
        employee,
        assignment,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.get(
        f"/employees/{employee.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == employee.id
    
@pytest.mark.asyncio
async def test_hrbp_cannot_get_employee_outside_assigned_team(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee
    from app.models.team import Team
    from app.models.department import Department
    from app.models.hrbp_team_assignment import HrbpTeamAssignment

    department = Department(
        name="Engineering",
        description="Engineering Department",
    )

    team_manager = Employee(
        username="team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )

    assigned_team = Team(
        name="Backend",
        department=department,
        team_manager=team_manager,
    )

    outside_team = Team(
        name="Frontend",
        department=department,
        team_manager=team_manager,
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee_outside_scope = Employee(
        username="employee2",
        full_name="Employee Two",
        join_date=date.today(),
        team=outside_team,
    )

    assignment = HrbpTeamAssignment(
        hrbp=hrbp,
        team=assigned_team,
    )

    db_session.add_all([
        department,
        team_manager,
        assigned_team,
        outside_team,
        hrbp,
        employee_outside_scope,
        assignment,
    ])

    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.get(
        f"/employees/{employee_outside_scope.id}"
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_get_employee_response_contract(
    client,
    db_session,
):
    from app.main import app
    from app.core.current_user import get_current_user, AuthenticatedUser
    from app.models.employee import Employee

    employee = Employee(
        username="employee",
        full_name="Test Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Test Employee",
        roles=["HR_MANAGER"],
    )

    response = await client.get(
        f"/employees/{employee.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert "username" in data
    assert "fullName" in data
    assert "nickname" in data
    assert "joinDate" in data
    assert "monthlySalary" in data

    assert "position" in data
    assert "team" in data
    assert "buddy" in data
    assert "hrManager" in data
    assert "hrbp" in data
    assert "directManager" in data
    assert "teamManager" in data
    assert "onboarding" in data
    assert "nextActions" in data

    assert "status" in data
    assert "roles" in data
    
    
@pytest.mark.asyncio
async def test_create_employee_without_token_returns_401(client):
    response = await client.post(
        "/employees",
        json={
            "username": "new_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": 1,
            "positionId": 1,
            "directManagerId": 1,
            "buddyId": 1,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_cannot_create_employee(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["EMPLOYEE"],
    )

    response = await client.post(
        "/employees",
        json={
            "username": "new_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": 1,
            "positionId": 1,
            "directManagerId": 1,
            "buddyId": 1,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_manager_cannot_create_employee(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.post(
        "/employees",
        json={
            "username": "new_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": 1,
            "positionId": 1,
            "directManagerId": 1,
            "buddyId": 1,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_hrbp_cannot_create_employee_outside_assigned_team(
    client,
    db_session,
):
    department = Department(
        name="Engineering",
        description="Backend department",
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        hrbp,
    ])

    await db_session.flush()

    position = Position(
        title="Backend Developer",
    )

    db_session.add(position)
    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()


    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.post(
        "/employees",
        json={
            "username": "new_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": team.id,
            "positionId": position.id,
            "directManagerId": manager.id,
            "buddyId": manager.id,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 403

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_hrbp_can_create_employee_in_assigned_team(
    client,
    db_session,
):
    department = Department(
        name="Engineering",
        description="Backend department",
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        nickname="mgr",
        join_date=date.today(),
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        nickname="hr",
        join_date=date.today(),
    )

    buddy = Employee(
        username="buddy",
        full_name="Buddy",
        nickname="buddy",
        join_date=date.today(),
    )

    position = Position(
        title="Backend Developer",
    )

    db_session.add_all([
        department,
        manager,
        hrbp,
        buddy,
        position,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.flush()

    assignment = HrbpTeamAssignment(
        hrbp_id=hrbp.id,
        team_id=team.id,
    )

    db_session.add(assignment)

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.post(
        "/employees",
        json={
            "username": "new_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": team.id,
            "positionId": position.id,
            "directManagerId": manager.id,
            "buddyId": buddy.id,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 201

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_employee_with_duplicate_username_returns_409(
    client,
    db_session,
):
    existing_employee = Employee(
        username="existing_employee",
        full_name="Existing Employee",
        nickname="existing",
        join_date=date.today(),
    )

    db_session.add(existing_employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=existing_employee.id,
        username="existing_employee",
        full_name="Existing Employee",
        roles=["HR_MANAGER"],
    )

    response = await client.post(
        "/employees",
        json={
            "username": "existing_employee",
            "fullName": "New Employee",
            "nickname": "new",
            "joinDate": "2026-08-18",
            "monthlySalary": 5000,
            "teamId": 1,
            "positionId": 1,
            "directManagerId": None,
            "buddyId": None,
            "onboardingStartDate": "2026-08-18",
            "onboardingDurationMonths": 3,
            "initialPassword": "password123",
        },
    )

    assert response.status_code == 409