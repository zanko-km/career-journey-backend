import pytest
from datetime import date
from app.models.onboarding import (
    Onboarding,
    OnboardingStatus,
    Decision,
    FinalResult,
)
from app.models import Employee, Onboarding
from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_employee_can_submit_continue_decision(
    client,
    db_session,
):

    employee = Employee(
        username="decision_employee",
        full_name="Decision Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=3,
        status=OnboardingStatus.FINAL_DECISION_PENDING,
    )

    db_session.add(onboarding)
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


    response = await client.post(
        f"/employees/{employee.id}/onboarding/employee-decision",
        json={
            "decision": "CONTINUE"
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert data["employeeDecision"] == "CONTINUE"
    assert data["managerDecision"] is None
    assert data["finalResult"] == "PENDING"
    
    
@pytest.mark.asyncio
async def test_employee_can_submit_exit_decision(
    client,
    db_session,
):

    employee = Employee(
        username="exit_employee",
        full_name="Exit Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=3,
        status=OnboardingStatus.FINAL_DECISION_PENDING,
    )

    db_session.add(onboarding)
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


    response = await client.post(
        f"/employees/{employee.id}/onboarding/employee-decision",
        json={
            "decision": "EXIT"
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert data["employeeDecision"] == "EXIT"
    assert data["finalResult"] == "EXIT"
    
    
@pytest.mark.asyncio
async def test_employee_cannot_submit_decision_for_other_employee(
    client,
    db_session,
):

    employee = Employee(
        username="target_employee",
        full_name="Target",
        join_date=date.today(),
    )

    other_employee = Employee(
        username="other_employee",
        full_name="Other",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            employee,
            other_employee
        ]
    )

    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        status=OnboardingStatus.FINAL_DECISION_PENDING,
        current_phase_number=3,
    )

    db_session.add(onboarding)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=other_employee.id,
        username="other",
        full_name="Other",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/employee-decision",
        json={
            "decision": "CONTINUE"
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_employee_cannot_submit_decision_before_final_phase(
    client,
    db_session,
):

    employee = Employee(
        username="early_decision",
        full_name="Early",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        status=OnboardingStatus.IN_PROGRESS,
        current_phase_number=2,
    )

    db_session.add(onboarding)
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


    response = await client.post(
        f"/employees/{employee.id}/onboarding/employee-decision",
        json={
            "decision": "CONTINUE"
        }
    )


    app.dependency_overrides.clear()


    assert response.status_code == 409