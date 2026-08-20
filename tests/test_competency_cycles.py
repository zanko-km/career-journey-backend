import pytest

from datetime import date, datetime

from app.main import app
from app.core.current_user import (
    get_current_user,
    AuthenticatedUser,
)
from app.models.competency import Competency
from app.models.employee_competency import EmployeeCompetency
from app.models.user import EmployeeRoleType
from app.models.employee import Employee
from app.models.competency_cycle import CompetencyCycle, CompetencyCyclePhase, CompetencyCycleStatus
from app.models.competency_self_assessment import CompetencySelfAssessment
from app.models.competency_manager_assessment import CompetencyManagerAssessment
from app.models.development_plan_items import DevelopmentPlanItem
from sqlalchemy import select
from app.models import HrbpTeamAssignment, Team, Department

@pytest.mark.asyncio
async def test_employee_can_list_own_competency_cycles(
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
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.get(
        f"/employees/{employee.id}/competency-cycles"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_employee_cannot_list_other_employee_competency_cycles(
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

    db_session.add_all(
        [
            employee1,
            employee2,
        ]
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
        f"/employees/{employee2.id}/competency-cycles"
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_hr_manager_can_list_any_employee_competency_cycles(
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
        employee_id=999,
        username="hr_manager",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.get(
        f"/employees/{employee.id}/competency-cycles"
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_competency_cycles_without_token_returns_401(
    client,
):

    response = await client.get(
        "/employees/1/competency-cycles"
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_not_found_returns_404(
    client,
):

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
        "/employees/99999/competency-cycles"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_competency_cycle_response_structure(
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
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.get(
        f"/employees/{employee.id}/competency-cycles"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_create_competency_cycle(
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
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/competency-cycles",
        json={
            "startDate": "2026-08-20",
            "endDate": "2027-02-20",
        },
    )


    assert response.status_code == 201

    data = response.json()

    assert data["employeeId"] == employee.id
    assert data["status"] == "ACTIVE"
    assert data["phase"] == "RATING"
    
@pytest.mark.asyncio
async def test_hrbp_can_create_competency_cycle(
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
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/competency-cycles",
        json={
            "startDate": "2026-08-20",
        },
    )


    assert response.status_code == 201
    
@pytest.mark.asyncio
async def test_employee_cannot_create_competency_cycle(
    client,
):

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        "/employees/1/competency-cycles",
        json={
            "startDate": "2026-08-20",
        },
    )


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_create_cycle_employee_not_found_returns_404(
    client,
):

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
        "/employees/99999/competency-cycles",
        json={
            "startDate": "2026-08-20",
        },
    )


    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_create_cycle_without_token_returns_401(
    client,
):

    response = await client.post(
        "/employees/1/competency-cycles",
        json={
            "startDate": "2026-08-20",
        },
    )


    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_employee_can_get_own_competency_cycle(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == cycle.id
    assert data["employeeId"] == employee.id
    assert data["status"] == "ACTIVE"
    assert data["phase"] == "RATING"
    
@pytest.mark.asyncio
async def test_employee_cannot_get_other_employee_competency_cycle(
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

    db_session.add_all([employee1, employee2])
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee2.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee1.id,
        username="employee1",
        full_name="Employee 1",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_get_any_competency_cycle(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == cycle.id
    
    
@pytest.mark.asyncio
async def test_manager_can_get_any_competency_cycle(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 200
    
    
@pytest.mark.asyncio
async def test_hrbp_can_get_any_competency_cycle(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=999,
        username="hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 200
    
    
@pytest.mark.asyncio
async def test_get_competency_cycle_not_found_returns_404(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        "/competency-cycles/99999"
    )

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_get_competency_cycle_without_token_returns_401(
    client,
):
    response = await client.get(
        "/competency-cycles/1"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_get_competency_cycle_response_structure(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert "employeeId" in data
    assert "startDate" in data
    assert "endDate" in data
    assert "status" in data
    assert "phase" in data
    assert "focusCompetencies" in data
    assert "meetingNotes" in data
    assert "meetingCompleted" in data
    assert "focusEndsAt" in data
    assert "reviewStartedAt" in data
    assert "reviewStartedBy" in data
    
    
@pytest.mark.asyncio
async def test_employee_can_submit_self_assessment(
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

    competency = Competency(
        name="Communication",
    )
    db_session.add(competency)
    await db_session.commit()

    employee_competency = EmployeeCompetency(
        employee_id=employee.id,
        competency_id=competency.id,
    )
    db_session.add(employee_competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": competency.id,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == cycle.id
    assert data["employeeId"] == employee.id
    assert data["status"] == "MANAGER_ASSESSMENT_PENDING"
    assert response.status_code == 200

    data = response.json()

    assert data["id"] == cycle.id
    assert data["employeeId"] == employee.id
    assert data["status"] == "MANAGER_ASSESSMENT_PENDING"
    
    
@pytest.mark.asyncio
async def test_employee_cannot_submit_self_assessment_for_other_employee(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    other_employee = Employee(
        username="other",
        full_name="Other Employee",
        join_date=date.today(),
    )

    db_session.add_all([employee, other_employee])
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=other_employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": 1,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 403
    

@pytest.mark.asyncio
async def test_non_employee_cannot_submit_self_assessment(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": 1,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_submit_self_assessment_cycle_not_found_returns_404(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/competency-cycles/999999/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": 1,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_self_assessment_requires_review_to_be_started(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": 1,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_submit_self_assessment_without_token_returns_401(
    client,
):
    response = await client.post(
        "/competency-cycles/1/self-assessment",
        json={
            "scores": [
                {
                    "competencyId": 1,
                    "score": 4,
                }
            ]
        },
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_manager_can_submit_manager_assessment(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee.manager = manager

    db_session.add_all([employee, manager])
    await db_session.commit()

    competency = Competency(
        name="Communication",
        description="Communication competency",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.MANAGER_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )

    db_session.add(cycle)
    await db_session.commit()

    self_assessment = CompetencySelfAssessment(
        cycle_id=cycle.id,
        competency_id=competency.id,
        score=4,
    )

    db_session.add(self_assessment)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={
            "scores": [
                {
                    "competencyId": competency.id,
                    "score": 5,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "MANAGER_ASSESSMENT_PENDING"



@pytest.mark.asyncio
async def test_manager_cannot_submit_before_employee_self_assessment(
    client,
    db_session,
):

    employee=Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    manager=Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee.manager=manager

    db_session.add_all(
        [
            employee,
            manager
        ]
    )

    await db_session.commit()


    cycle=CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )


    db_session.add(cycle)

    await db_session.commit()


    app.dependency_overrides[get_current_user]=lambda:AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response=await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={
            "scores":[
                {
                    "competencyId":1,
                    "score":5
                }
            ]
        }
    )


    assert response.status_code==409



@pytest.mark.asyncio
async def test_manager_cannot_submit_other_employee_assessment(
    client,
    db_session,
):

    employee=Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    manager1=Employee(
        username="manager1",
        full_name="Manager1",
        join_date=date.today(),
    )

    manager2=Employee(
        username="manager2",
        full_name="Manager2",
        join_date=date.today(),
    )


    employee.manager=manager1


    db_session.add_all(
        [
            employee,
            manager1,
            manager2
        ]
    )

    await db_session.commit()


    cycle=CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )


    db_session.add(cycle)
    await db_session.commit()



    app.dependency_overrides[get_current_user]=lambda:AuthenticatedUser(
        id=1,
        employee_id=manager2.id,
        username="manager2",
        full_name="Manager2",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response=await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={
            "scores":[
                {
                    "competencyId":1,
                    "score":5
                }
            ]
        }
    )


    assert response.status_code==403



@pytest.mark.asyncio
async def test_employee_cannot_submit_manager_assessment(
    client,
):

    app.dependency_overrides[get_current_user]=lambda:AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response=await client.post(
        "/competency-cycles/1/manager-assessment",
        json={
            "scores":[
                {
                    "competencyId":1,
                    "score":5
                }
            ]
        }
    )


    assert response.status_code==403



@pytest.mark.asyncio
async def test_manager_assessment_cycle_not_found(
    client,
):

    app.dependency_overrides[get_current_user]=lambda:AuthenticatedUser(
        id=1,
        employee_id=1,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response=await client.post(
        "/competency-cycles/99999/manager-assessment",
        json={
            "scores":[
                {
                    "competencyId":1,
                    "score":5
                }
            ]
        }
    )


    assert response.status_code==404



@pytest.mark.asyncio
async def test_manager_assessment_without_token_returns_401(
    client,
):

    response=await client.post(
        "/competency-cycles/1/manager-assessment",
        json={
            "scores":[
                {
                    "competencyId":1,
                    "score":5
                }
            ]
        }
    )


    assert response.status_code==401
    
    
@pytest.mark.asyncio
async def test_employee_can_get_radar_data(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    employee.manager = manager

    db_session.add_all([employee, manager])
    await db_session.commit()

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )
    cycle.focus_competencies.append(competency)
    db_session.add(cycle)
    await db_session.commit()

    db_session.add_all(
        [
            CompetencySelfAssessment(
                cycle_id=cycle.id,
                competency_id=competency.id,
                score=4,
            ),
            CompetencyManagerAssessment(
                cycle_id=cycle.id,
                competency_id=competency.id,
                score=5,
            ),
        ]
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}/radar-data"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["labels"] == ["Communication"]
    assert data["employeeScores"] == [4]
    assert data["managerScores"] == [5]
    
    
@pytest.mark.asyncio
async def test_radar_data_requires_manager_assessment(
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

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )

    db_session.add(cycle)
    await db_session.commit()

    db_session.add(
        CompetencySelfAssessment(
            cycle_id=cycle.id,
            competency_id=competency.id,
            score=4,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}/radar-data"
    )

    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_radar_data_requires_review_started(
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

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.SELF_ASSESSMENT_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=None,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}/radar-data"
    )

    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_radar_data_cycle_not_found(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        "/competency-cycles/999999/radar-data"
    )

    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_radar_data_without_token_returns_401(
    client,
):
    response = await client.get(
        "/competency-cycles/1/radar-data"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_employee_can_get_own_idp(
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

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )

    db_session.add(cycle)
    await db_session.commit()

    item = DevelopmentPlanItem(
        cycle_id=cycle.id,
        competency_id=competency.id,
        author_id=employee.id,
        author_role=EmployeeRoleType.EMPLOYEE,
        comment="Improve communication",
        completed=False,
    )

    db_session.add(item)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}/idp"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["employeeItems"]) == 1
    assert data["employeeItems"][0]["comment"] == "Improve communication"
    assert data["hrbpItems"] == []
    
    
@pytest.mark.asyncio
async def test_employee_can_submit_idp_item(
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

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "Need more practice",
                    "completed": False,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["comment"] == "Need more practice"
    
    
@pytest.mark.asyncio
async def test_employee_idp_upsert_updates_existing_item(
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

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
        review_started_at=datetime.now(),
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    payload = {
        "items": [
            {
                "competencyId": competency.id,
                "comment": "old",
                "completed": False,
            }
        ]
    }

    await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json=payload,
    )

    await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "new",
                    "completed": True,
                }
            ]
        },
    )

    result = await db_session.execute(
        select(DevelopmentPlanItem).where(
            DevelopmentPlanItem.cycle_id == cycle.id
        )
    )

    items = result.scalars().all()

    assert len(items) == 1
    assert items[0].comment == "new"
    assert items[0].completed is True
    
    
@pytest.mark.asyncio
async def test_employee_cannot_get_other_employee_idp(
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

    db_session.add_all([employee1, employee2])
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee2.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee1.id,
        username="employee1",
        full_name="Employee 1",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/competency-cycles/{cycle.id}/idp"
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_get_idp_cycle_not_found_returns_404(
    client,
):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        "/competency-cycles/99999/idp"
    )

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_employee_cannot_submit_unassigned_competency(
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

    competency = Competency(
        name="Python",
        description="Python",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "learn",
                    "completed": False,
                }
            ]
        },
    )

    assert response.status_code == 400
    
    
@pytest.mark.asyncio
async def test_employee_cannot_submit_other_employee_cycle_idp(
    client,
    db_session,
):
    owner = Employee(
        username="owner",
        full_name="Owner",
        join_date=date.today(),
    )

    attacker = Employee(
        username="attacker",
        full_name="Attacker",
        join_date=date.today(),
    )

    db_session.add_all([owner, attacker])
    await db_session.commit()

    cycle = CompetencyCycle(
        employee_id=owner.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=attacker.id,
        username="attacker",
        full_name="Attacker",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": []
        },
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_idp_author_is_taken_from_authenticated_user(
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

    competency = Competency(
        name="Communication",
        description="Communication",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=999,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "test",
                    "completed": False,
                    "authorId": 999999,
                    "authorRole": "HR_MANAGER",
                }
            ]
        },
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(DevelopmentPlanItem)
    )

    item = result.scalar_one()

    assert item.author_id == employee.id
    assert item.author_role == EmployeeRoleType.EMPLOYEE
    
    
@pytest.mark.asyncio
async def test_employee_idp_multiple_items_created(
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

    c1 = Competency(
        name="Python",
        description="Python",
        active=True,
    )

    c2 = Competency(
        name="SQL",
        description="SQL",
        active=True,
    )

    db_session.add_all([c1, c2])
    await db_session.commit()

    db_session.add_all([
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=c1.id,
        ),
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=c2.id,
        )
    ])

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": c1.id,
                    "comment": "python",
                    "completed": False,
                },
                {
                    "competencyId": c2.id,
                    "comment": "sql",
                    "completed": True,
                }
            ]
        },
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(DevelopmentPlanItem)
        .where(
            DevelopmentPlanItem.cycle_id == cycle.id
        )
    )

    items = result.scalars().all()

    assert len(items) == 2
    
    
@pytest.mark.asyncio
async def test_hrbp_can_submit_idp_item(
    client,
    db_session,
):
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )

    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    db_session.add_all([
        employee,
        hrbp,
        manager,
    ])

    await db_session.commit()

    department = Department(
        name="Engineering",
    )

    db_session.add(department)
    await db_session.commit()

    team = Team(
        name="Backend Team",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.commit()

    db_session.add_all([
        employee,
        hrbp,
        team,
    ])
    await db_session.commit()

    assignment = HrbpTeamAssignment(
        hrbp_id=hrbp.id,
        team_id=team.id,
    )

    db_session.add(assignment)

    await db_session.commit()
    
    employee.team_id = team.id


    competency = Competency(
        name="Python",
        description="Python",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()

    db_session.add(
        EmployeeCompetency(
            employee_id=employee.id,
            competency_id=competency.id,
        )
    )

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
        phase=CompetencyCyclePhase.RATING,
    )

    db_session.add(cycle)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "Improve Python",
                    "completed": False,
                }
            ]
        },
    )


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["authorRole"] == "HRBP"
    assert data[0]["authorId"] == hrbp.id
    
    
@pytest.mark.asyncio
async def test_hrbp_cannot_submit_idp_for_unassigned_team_employee(
    client,
    db_session,
):

    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )


    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )


    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    db_session.add_all([
        employee,
        hrbp,
        manager,
    ])

    await db_session.commit()

    department = Department(
        name="Engineering",
    )

    db_session.add(department)
    await db_session.commit()

    team = Team(
        name="Backend Team",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)

    await db_session.commit()

    db_session.add_all([
        employee,
        hrbp,
        team,
    ])

    await db_session.commit()


    employee.team_id = team.id


    # HRBP assigned to another team
    another_team = Team(
        name="HRBP Team",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(another_team)
    await db_session.commit()


    db_session.add(
        HrbpTeamAssignment(
            hrbp_id=hrbp.id,
            team_id=another_team.id,
        )
    )


    competency = Competency(
        name="Python",
        active=True,
    )

    db_session.add(competency)
    await db_session.commit()


    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
    )


    db_session.add(cycle)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": [
                {
                    "competencyId": competency.id,
                    "comment": "test",
                    "completed": False,
                }
            ]
        },
    )


    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_manager_cannot_submit_idp(
    client,
    db_session,
):

    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )


    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )


    db_session.add_all([
        employee,
        manager,
    ])

    await db_session.commit()


    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
    )

    db_session.add(cycle)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=3,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )


    response = await client.post(
        f"/competency-cycles/{cycle.id}/idp",
        json={
            "items": []
        },
    )


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_employee_and_hrbp_idp_are_separated(
    client,
    db_session,
):

    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
    )


    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )


    db_session.add_all([
        employee,
        hrbp,
    ])

    await db_session.commit()


    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today(),
        status=CompetencyCycleStatus.REVIEW_PENDING,
    )

    db_session.add(cycle)


    competency = Competency(
        name="Python",
        active=True,
    )

    db_session.add(competency)

    await db_session.commit()


    db_session.add_all([
        DevelopmentPlanItem(
            cycle_id=cycle.id,
            competency_id=competency.id,
            author_id=employee.id,
            author_role=EmployeeRoleType.EMPLOYEE,
            comment="employee",
            completed=False,
        ),

        DevelopmentPlanItem(
            cycle_id=cycle.id,
            competency_id=competency.id,
            author_id=hrbp.id,
            author_role=EmployeeRoleType.HRBP,
            comment="hrbp",
            completed=False,
        )
    ])


    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )


    response = await client.get(
        f"/competency-cycles/{cycle.id}/idp"
    )


    assert response.status_code == 200

    data = response.json()


    assert len(data["employeeItems"]) == 1
    assert len(data["hrbpItems"]) == 1

    assert data["employeeItems"][0]["authorRole"] == "EMPLOYEE"
    assert data["hrbpItems"][0]["authorRole"] == "HRBP"
    
    
