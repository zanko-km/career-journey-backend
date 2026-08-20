from datetime import date

import pytest

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_get_employee_onboarding_feedback(
    client,
    db_session,
):
    employee = Employee(
        username="feedback_user",
        full_name="Feedback User",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=1,
    )

    db_session.add(onboarding)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.get(
        f"/employees/{employee.id}/onboarding/feedback"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200
    assert response.json() == []
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_feedback_without_auth_returns_401(
    client,
):

    response = await client.get(
        "/employees/1/onboarding/feedback"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_get_employee_onboarding_feedback_not_found(
    client,
    db_session,
):

    employee = Employee(
        username="feedback_not_found",
        full_name="Not Found",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.get(
        f"/employees/{employee.id}/onboarding/feedback"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_feedback(
    client,
    db_session,
):

    employee = Employee(
        username="feedback_create",
        full_name="Feedback Create",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=1,
    )

    db_session.add(onboarding)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/feedback",
        json={
            "feedback": "Good onboarding experience",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 201

    data = response.json()

    assert data["feedback"] == "Good onboarding experience"
    assert data["employeeId"] == employee.id
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_feedback_without_auth_returns_401(
    client,
):

    response = await client.post(
        "/employees/1/onboarding/feedback",
        json={
            "feedback": "test",
        },
    )


    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_feedback_not_found(
    client,
    db_session,
):

    employee = Employee(
        username="feedback_missing_onboarding",
        full_name="Missing",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="hr",
        full_name="HR",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/feedback",
        json={
            "feedback": "test",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_feedback_forbidden_role(
    client,
    db_session,
):

    employee = Employee(
        username="feedback_forbidden",
        full_name="Forbidden",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()


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
        f"/employees/{employee.id}/onboarding/feedback",
        json={
            "feedback": "test",
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_create_employee_onboarding_feedback_validation_error(
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
        "/employees/1/onboarding/feedback",
        json={}
    )

    assert response.status_code == 422