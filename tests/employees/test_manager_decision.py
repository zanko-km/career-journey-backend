import pytest
from datetime import date

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser

from app.models.employee import Employee
from app.models.onboarding import (
    Onboarding,
    OnboardingStatus,
)
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_manager_can_submit_continue_decision(
    client,
    db_session,
):

    manager = Employee(
        username="manager_continue",
        full_name="Manager Continue",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_continue",
        full_name="Employee Continue",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()

    employee.manager_id = manager.id


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
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "CONTINUE"
        },
    )


    assert response.status_code == 200

    data = response.json()

    assert data["managerDecision"] == "CONTINUE"



@pytest.mark.asyncio
async def test_manager_can_submit_exit_decision(
    client,
    db_session,
):

    manager = Employee(
        username="manager_exit",
        full_name="Manager Exit",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_exit",
        full_name="Employee Exit",
        join_date=date.today(),
        manager_id=None,
    )


    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()

    employee.manager_id = manager.id


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
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "EXIT",
            "exitType": "RESIGNATION"
        },
    )


    assert response.status_code == 200

    data = response.json()

    assert data["managerDecision"] == "EXIT"
    assert data["finalResult"] == "EXIT"



@pytest.mark.asyncio
async def test_manager_cannot_submit_for_other_employee(
    client,
    db_session,
):

    real_manager = Employee(
        username="real_manager",
        full_name="Real Manager",
        join_date=date.today(),
    )


    fake_manager = Employee(
        username="fake_manager",
        full_name="Fake Manager",
        join_date=date.today(),
    )


    employee = Employee(
        username="target_employee",
        full_name="Target Employee",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            real_manager,
            fake_manager,
            employee,
        ]
    )


    await db_session.flush()

    employee.manager_id = real_manager.id


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
        employee_id=fake_manager.id,
        username="fake_manager",
        full_name="Fake Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "CONTINUE"
        },
    )


    assert response.status_code == 403



@pytest.mark.asyncio
async def test_hr_manager_can_submit_manager_decision(
    client,
    db_session,
):

    hr_manager = Employee(
        username="hr_manager",
        full_name="HR Manager",
        join_date=date.today(),
    )


    employee = Employee(
        username="employee_hr",
        full_name="Employee HR",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            hr_manager,
            employee,
        ]
    )

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
        employee_id=hr_manager.id,
        username="hr_manager",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "CONTINUE"
        },
    )


    assert response.status_code == 200



@pytest.mark.asyncio
async def test_manager_decision_without_onboarding_returns_404(
    client,
    db_session,
):

    manager = Employee(
        username="no_onboarding_manager",
        full_name="Manager",
        join_date=date.today(),
    )


    employee = Employee(
        username="no_onboarding_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=None,
    )


    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()

    employee.manager_id = manager.id

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
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "CONTINUE"
        },
    )


    assert response.status_code == 404



@pytest.mark.asyncio
async def test_manager_decision_when_onboarding_not_pending_returns_409(
    client,
    db_session,
):

    manager = Employee(
        username="wrong_status_manager",
        full_name="Manager",
        join_date=date.today(),
    )


    employee = Employee(
        username="wrong_status_employee",
        full_name="Employee",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()

    employee.manager_id = manager.id


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=1,
        status=OnboardingStatus.IN_PROGRESS,
    )


    db_session.add(onboarding)

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
        f"/employees/{employee.id}/onboarding/manager-decision",
        json={
            "decision": "CONTINUE"
        },
    )


    assert response.status_code == 409



@pytest.mark.asyncio
async def test_manager_decision_invalid_payload_returns_422(
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
        "/employees/1/onboarding/manager-decision",
        json={
            "decision": "INVALID"
        },
    )


    assert response.status_code == 422