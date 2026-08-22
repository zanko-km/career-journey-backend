import pytest
from app.main import app
from app.core.current_user import AuthenticatedUser, get_current_user
from datetime import date
from app.models import Department, Employee, HrbpTeamAssignment, Team
from app.models.user import EmployeeRoleType

@pytest.mark.asyncio
async def test_only_hr_manager_can_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,employee_id=1, username="ali", full_name="Ali", roles=["EMPLOYEE"]
    )
    response = await client.post("/teams", json={
    "name": "Backend",
    "departmentId": 1,
    "teamManagerId": 1
    })
    assert response.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_hr_manager_can_create_team(client, db_session):

    department = Department(
        name="Engineering",
        description="Backend department"
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        nickname="mgr",
        join_date=date.today()
    )

    db_session.add_all([department, manager])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"]
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": department.id,
            "teamManagerId": manager.id
        }
    )

    assert response.status_code == 201
    

@pytest.mark.asyncio  
async def test_get_teams_without_token_returns_401(client):
    response = await client.get("/teams")

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_employee_cannot_get_teams(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["EMPLOYEE"]
    )

    response = await client.get("/teams")

    assert response.status_code == 403

@pytest.mark.asyncio
async def test_hr_manager_can_get_teams(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"]
    )

    response = await client.get("/teams")

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_hrbp_can_get_teams(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HRBP"]
    )

    response = await client.get("/teams")

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_hr_manager_can_create_team(client, db_session):
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

    db_session.add_all([department, manager])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": department.id,
            "teamManagerId": manager.id,
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["name"] == "Backend"
    assert body["department"]["id"] == department.id
    assert body["department"]["name"] == "Engineering"
    assert body["teamManager"]["id"] == manager.id
    
@pytest.mark.asyncio
async def test_create_team_without_token_returns_401(client):
    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": 1,
            "teamManagerId": 1,
        },
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_employee_cannot_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["EMPLOYEE"],
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": 1,
            "teamManagerId": 1,
        },
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_manager_cannot_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["MANAGER"],
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": 1,
            "teamManagerId": 1,
        },
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_hrbp_cannot_create_team(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HRBP"],
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
            "departmentId": 1,
            "teamManagerId": 1,
        },
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_create_team_with_invalid_body_returns_422(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.post(
        "/teams",
        json={
            "name": "Backend",
        },
    )

    assert response.status_code == 422
    
@pytest.mark.asyncio
async def test_manager_can_get_teams(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["MANAGER"],
    )

    response = await client.get("/teams")

    assert response.status_code == 200
    
@pytest.mark.asyncio
async def test_get_teams_response_contract(
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

    db_session.add_all([department, manager])
    await db_session.commit()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get("/teams")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) >= 1

    item = body[0]

    assert "id" in item
    assert "name" in item
    assert "department" in item
    assert "teamManager" in item
    assert "hrbps" in item

    assert item["name"] == "Backend"
    assert item["department"]["id"] == department.id
    assert item["teamManager"]["id"] == manager.id
    assert isinstance(item["hrbps"], list)
    
@pytest.mark.asyncio
async def test_get_teams_returns_assigned_hrbps(
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
        full_name="HRBP User",
        nickname="hr",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        hrbp,
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
        id=hrbp.id,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP User",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )

    response = await client.get("/teams")

    assert response.status_code == 200

    body = response.json()

    team_data = next(
        item for item in body
        if item["id"] == team.id
    )

    assert len(team_data["hrbps"]) == 1
    assert team_data["hrbps"][0]["id"] == hrbp.id
    assert team_data["hrbps"][0]["fullName"] == "HRBP User"
    
@pytest.mark.asyncio
async def test_get_team_without_token_returns_401(
    client,
    db_session,
):
    response = await client.get("/teams/1")

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_employee_cannot_get_team(
    client,
    db_session,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["EMPLOYEE"],
    )

    response = await client.get("/teams/1")

    assert response.status_code == 403

@pytest.mark.asyncio
async def test_manager_can_get_team(
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

    db_session.add_all([department, manager])
    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(f"/teams/{team.id}")

    assert response.status_code == 200
    
@pytest.mark.asyncio
async def test_hrbp_can_get_team(
    client,
    db_session,
):

    department = Department(
        name="Engineering",
        description="Backend department",
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        nickname="mgr",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            department,
            hrbp,
            manager,
        ]
    )

    await db_session.flush()


    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.flush()


    db_session.add(
        HrbpTeamAssignment(
            hrbp_id=hrbp.id,
            team_id=team.id,
        )
    )

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=hrbp.id,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.get(
        f"/teams/{team.id}"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200
    
@pytest.mark.asyncio
async def test_hr_manager_can_get_team(
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

    db_session.add_all([department, manager])
    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get(f"/teams/{team.id}")

    assert response.status_code == 200
    
@pytest.mark.asyncio
async def test_get_team_not_found(
    client,
    db_session,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get("/teams/999999")

    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_get_team_response_contract(
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
        job_title="Engineering Manager",
        join_date=date.today(),
    )

    db_session.add_all([department, manager])
    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get(f"/teams/{team.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == team.id
    assert data["name"] == "Backend"

    assert data["department"]["id"] == department.id
    assert data["department"]["name"] == "Engineering"

    assert data["teamManager"]["id"] == manager.id
    assert data["teamManager"]["fullName"] == "Manager"
    assert data["teamManager"]["nickname"] == "mgr"
    assert data["teamManager"]["jobTitle"] == "Engineering Manager"

    assert "hrbps" in data
    assert isinstance(data["hrbps"], list)
    
@pytest.mark.asyncio
async def test_get_team_returns_assigned_hrbps(
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
        full_name="HRBP User",
        nickname="hr",
        job_title="HR Business Partner",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        hrbp,
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
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get(f"/teams/{team.id}")

    assert response.status_code == 200

    data = response.json()

    assert len(data["hrbps"]) == 1
    assert data["hrbps"][0]["id"] == hrbp.id
    assert data["hrbps"][0]["fullName"] == "HRBP User"
    assert data["hrbps"][0]["nickname"] == "hr"
    assert data["hrbps"][0]["jobTitle"] == "HR Business Partner"
    
# ============================================================
# GET /teams/{teamId}/employees
# ============================================================


@pytest.mark.asyncio
async def test_get_team_employees_without_token_returns_401(
    client,
):
    response = await client.get("/teams/1/employees")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_cannot_get_team_employees(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=["EMPLOYEE"],
    )

    response = await client.get("/teams/1/employees")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_get_team_employees(
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

    employee = Employee(
        username="employee",
        full_name="Employee",
        nickname="emp",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        employee,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()

    employee.team_id = team.id

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(
        f"/teams/{team.id}/employees"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == employee.id
    assert data[0]["fullName"] == "Employee"


@pytest.mark.asyncio
async def test_hrbp_can_get_team_employees(
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
        nickname="hr",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee",
        full_name="Employee",
        nickname="emp",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        hrbp,
        employee,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()

    employee.team_id = team.id

    assignment = HrbpTeamAssignment(
        hrbp_id=hrbp.id,
        team_id=team.id,
    )

    db_session.add(assignment)

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=["HRBP"],
    )

    response = await client.get(
        f"/teams/{team.id}/employees"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == employee.id
    assert data[0]["fullName"] == "Employee"


@pytest.mark.asyncio
async def test_hr_manager_can_get_team_employees(
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

    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        employee,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()

    employee.team_id = team.id

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get(
        f"/teams/{team.id}/employees"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == employee.id


@pytest.mark.asyncio
async def test_get_team_employees_not_found(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="ali",
        full_name="Ali",
        roles=["HR_MANAGER"],
    )

    response = await client.get(
        "/teams/999999/employees"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_team_employees_returns_empty_list_when_team_has_no_employees(
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

    db_session.add_all([
        department,
        manager,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(
        f"/teams/{team.id}/employees"
    )

    assert response.status_code == 200

    assert response.json() == []


@pytest.mark.asyncio
async def test_get_team_employees_returns_only_requested_team_employees(
    client,
    db_session,
):
    department = Department(
        name="Engineering",
        description="Backend department",
    )

    manager_a = Employee(
        username="manager_a",
        full_name="Manager A",
        join_date=date.today(),
    )

    manager_b = Employee(
        username="manager_b",
        full_name="Manager B",
        join_date=date.today(),
    )

    employee_a = Employee(
        username="employee_a",
        full_name="Employee A",
        join_date=date.today(),
    )

    employee_b = Employee(
        username="employee_b",
        full_name="Employee B",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager_a,
        manager_b,
        employee_a,
        employee_b,
    ])

    await db_session.flush()

    team_a = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager_a.id,
    )

    team_b = Team(
        name="Frontend",
        department_id=department.id,
        team_manager_id=manager_b.id,
    )

    db_session.add_all([
        team_a,
        team_b,
    ])

    await db_session.flush()

    employee_a.team_id = team_a.id
    employee_b.team_id = team_b.id

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager_a.id,
        username="manager_a",
        full_name="Manager A",
        roles=["MANAGER"],
    )

    response = await client.get(
        f"/teams/{team_a.id}/employees"
    )

    assert response.status_code == 200

    data = response.json()

    employee_ids = {
        employee["id"]
        for employee in data
    }

    assert employee_a.id in employee_ids
    assert employee_b.id not in employee_ids


@pytest.mark.asyncio
async def test_get_team_employees_response_contract(
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
        job_title="Engineering Manager",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee",
        full_name="John Doe",
        nickname="john",
        job_title="Backend Developer",
        join_date=date.today(),
    )

    db_session.add_all([
        department,
        manager,
        employee,
    ])

    await db_session.flush()

    team = Team(
        name="Backend",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.flush()

    employee.team_id = team.id

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=["MANAGER"],
    )

    response = await client.get(
        f"/teams/{team.id}/employees"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    employee_data = data[0]

    assert employee_data["id"] == employee.id
    assert employee_data["fullName"] == "John Doe"
    assert employee_data["nickname"] == "john"
    assert employee_data["jobTitle"] == "Backend Developer"

    assert "status" in employee_data
    assert "careerStage" in employee_data
    assert "onboardingPhase" in employee_data