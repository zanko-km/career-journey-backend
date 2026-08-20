import pytest
from app.main import app
from datetime import date
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.user import EmployeeRoleType
from app.models.competency import Competency
from app.models.employee_competency import EmployeeCompetency
from app.models.employee import Employee

@pytest.mark.asyncio
async def test_employee_can_list_competencies(
    client,
    db_session,
):
    competency = Competency(
        name="Communication",
        description="Ability to communicate effectively",
        active=True,
    )

    db_session.add(competency)

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.get(
        "/competencies"
    )


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Communication"
    assert data[0]["active"] is True
    
    
@pytest.mark.asyncio
async def test_only_active_competencies_are_returned(
    client,
    db_session,
):
    db_session.add_all(
        [
            Competency(
                name="Active Competency",
                active=True,
            ),
            Competency(
                name="Inactive Competency",
                active=False,
            ),
        ]
    )

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.get(
        "/competencies"
    )


    assert response.status_code == 200

    data = response.json()

    names = [
        item["name"]
        for item in data
    ]

    assert "Active Competency" in names
    assert "Inactive Competency" not in names
    
@pytest.mark.asyncio
async def test_list_competencies_without_token_returns_401(
    client,
):
    response = await client.get(
        "/competencies"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_create_competency(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr_manager",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )

    response = await client.post(
        "/competencies",
        json={
            "name": "Communication",
            "description": "Ability to communicate effectively",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Communication"
    assert data["description"] == "Ability to communicate effectively"
    assert data["active"] is True
    
@pytest.mark.asyncio
async def test_manager_cannot_create_competency(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )

    response = await client.post(
        "/competencies",
        json={
            "name": "Leadership",
            "description": "Lead teams",
        },
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_create_competency_without_token_returns_401(
    client,
):
    response = await client.post(
        "/competencies",
        json={
            "name": "Leadership",
            "description": "Lead teams",
        },
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_create_duplicate_competency_returns_409(
    client,
    db_session,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr_manager",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )

    competency = Competency(
        name="Leadership",
        description="Existing",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()


    response = await client.post(
        "/competencies",
        json={
            "name": "Leadership",
            "description": "New",
        },
    )


    assert response.status_code == 409
    
@pytest.mark.asyncio
async def test_create_competency_invalid_payload_returns_422(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr_manager",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )

    response = await client.post(
        "/competencies",
        json={
            "description": "missing name"
        },
    )

    assert response.status_code == 422
    
@pytest.mark.asyncio
async def test_employee_can_see_own_competencies(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    competency = Competency(
        name="Communication",
        description="Communication skill",
        active=True,
    )

    db_session.add_all(
        [
            employee,
            competency,
        ]
    )

    await db_session.flush()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        f"/employees/{employee.id}/competencies"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Communication"
    
@pytest.mark.asyncio
async def test_employee_cannot_see_other_employee_competencies(
    client,
    db_session,
):
    employee1 = Employee(
        username="employee1",
        full_name="Employee 1",
        join_date=date.today(),
    )

    employee2 = Employee(
        username="employee2",
        full_name="Employee 2",
        join_date=date.today(),
    )

    competency = Competency(
        name="Leadership",
        active=True,
    )

    db_session.add_all(
        [
            employee1,
            employee2,
            competency,
        ]
    )

    await db_session.flush()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee2.id,
            competency_id=competency.id,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee1.id,
        username="employee1",
        full_name="Employee 1",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        f"/employees/{employee2.id}/competencies"
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_get_employee_competencies_without_token_returns_401(
    client,
):

    response = await client.get(
        "/employees/1/competencies"
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_get_employee_competencies_employee_not_found_returns_404(
    client,
):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        "/employees/999/competencies"
    )

    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_hr_manager_can_see_any_employee_competencies(
    client,
    db_session,
):

    employee = Employee(
        username="target",
        full_name="Target",
        join_date=date.today(),
    )

    competency = Competency(
        name="Problem Solving",
        active=True,
    )

    db_session.add_all(
        [
            employee,
            competency,
        ]
    )

    await db_session.flush()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.get(
        f"/employees/{employee.id}/competencies"
    )


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Problem Solving"
    
@pytest.mark.asyncio
async def test_hr_manager_can_assign_competencies(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    competency = Competency(
        name="Communication",
        description="Ability to communicate",
        active=True,
    )

    db_session.add_all(
        [
            employee,
            competency,
        ]
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )

    response = await client.post(
        f"/employees/{employee.id}/competencies",
        json={
            "competencyIds": [
                competency.id
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == competency.id
    
@pytest.mark.asyncio
async def test_hrbp_can_assign_competencies(
    client,
    db_session,
):
    employee = Employee(
        username="employee2",
        full_name="Employee",
        join_date=date.today(),
    )

    competency = Competency(
        name="Leadership",
        active=True,
    )

    db_session.add_all(
        [
            employee,
            competency,
        ]
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )

    response = await client.post(
        f"/employees/{employee.id}/competencies",
        json={
            "competencyIds":[competency.id]
        }
    )

    assert response.status_code == 200
    
@pytest.mark.asyncio
async def test_manager_cannot_assign_competencies(
    client,
):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )

    response = await client.post(
        "/employees/1/competencies",
        json={
            "competencyIds":[1]
        }
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_assign_competency_without_token_returns_401(
    client,
):

    response = await client.post(
        "/employees/1/competencies",
        json={
            "competencyIds":[1]
        }
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_assign_competencies_employee_not_found_returns_404(
    client,
    db_session,
):

    competency = Competency(
        name="Communication",
        active=True,
    )

    db_session.add(competency)

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        "/employees/9999/competencies",
        json={
            "competencyIds":[competency.id]
        }
    )

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_assign_non_existing_competency_returns_404(
    client,
    db_session,
):

    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add(employee)

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/competencies",
        json={
            "competencyIds":[99999]
        }
    )

    assert response.status_code == 404