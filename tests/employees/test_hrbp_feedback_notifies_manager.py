"""
Tests for closing Gap C: submitting month-1 HRBP onboarding feedback must
notify the employee's direct manager.

`POST /employees/{employee_id}/onboarding/feedback` previously only saved
the feedback row with no notification at all. The manager could see it via
`GET /employees/{employee_id}/onboarding/feedback` (already allowed for
MANAGER), but had no way to know it existed without checking manually.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Employee, Notification, User
from app.models.onboarding import Onboarding
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_hrbp_feedback_notifies_direct_manager(
    client,
    db_session,
):
    manager = Employee(
        username="feedback_notify_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    manager_user = User(
        auth_provider_id="auth-feedback-notify-manager",
        employee_id=manager.id,
    )
    db_session.add(manager_user)
    await db_session.flush()

    hrbp = Employee(
        username="feedback_notify_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="feedback_notify_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=99,
        employee_id=hrbp.id,
        username="feedback_notify_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/feedback",
        json={
            "feedback": "Great first month, settling in well.",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201

    result = await db_session.execute(
        select(Notification).where(Notification.user_id == manager_user.id)
    )
    notifications = result.scalars().all()

    assert len(notifications) == 1
    assert notifications[0].reference_type == "ONBOARDING_FEEDBACK"


@pytest.mark.asyncio
async def test_hrbp_feedback_does_not_error_when_employee_has_no_manager(
    client,
    db_session,
):
    """Regression guard: an employee with no manager (manager_id is None)
    must not break feedback creation."""

    hrbp = Employee(
        username="feedback_no_manager_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="feedback_no_manager_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=None,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=99,
        employee_id=hrbp.id,
        username="feedback_no_manager_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/feedback",
        json={
            "feedback": "No manager assigned yet.",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_manager_can_see_the_feedback_notification_was_created_for_them(
    client,
    db_session,
):
    """End-to-end: manager has no User row missing pitfalls -- notification
    is actually queryable via the notifications table with the right
    message content referencing the employee."""

    manager = Employee(
        username="feedback_notify_manager_e2e",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    manager_user = User(
        auth_provider_id="auth-feedback-notify-manager-e2e",
        employee_id=manager.id,
    )
    db_session.add(manager_user)
    await db_session.flush()

    hrbp = Employee(
        username="feedback_notify_hrbp_e2e",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="feedback_notify_employee_e2e",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=99,
        employee_id=hrbp.id,
        username="feedback_notify_hrbp_e2e",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )

    await client.post(
        f"/employees/{employee.id}/onboarding/feedback",
        json={"feedback": "Doing great."},
    )

    app.dependency_overrides.clear()

    result = await db_session.execute(
        select(Notification).where(Notification.user_id == manager_user.id)
    )
    notification = result.scalar_one()

    assert str(employee.id) in notification.message
