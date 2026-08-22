import pytest
from app.models import Employee, Notification, User
from app.models.user import EmployeeRoleType
from app.core.current_user import get_current_user, AuthenticatedUser
from app.main import app
from datetime import date, datetime, timedelta


@pytest.mark.asyncio
async def test_user_can_list_notifications(
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


    user = User(
        employee_id=employee.id,
        auth_provider_id="test-auth-id",
    )

    db_session.add(user)
    await db_session.commit()


    notification = Notification(
        user_id=user.id,
        type="MEETING_CREATED",
        message="Meeting created",
    )

    db_session.add(notification)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=user.id,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )


    response = await client.get(
        "/notifications"
    )


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["type"] == "MEETING_CREATED"
    
    
@pytest.mark.asyncio
async def test_list_notifications_without_token_returns_401(
    client,
):
    app.dependency_overrides.pop(get_current_user, None)

    response = await client.get("/notifications")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_can_only_see_own_notifications(
    client,
    db_session,
):
    employee_1 = Employee(
        username="employee1",
        full_name="Employee 1",
        join_date=date.today(),
    )

    employee_2 = Employee(
        username="employee2",
        full_name="Employee 2",
        join_date=date.today(),
    )

    db_session.add_all([employee_1, employee_2])
    await db_session.commit()

    user_1 = User(
        employee_id=employee_1.id,
        auth_provider_id="test-auth-id-1",
    )

    user_2 = User(
        employee_id=employee_2.id,
        auth_provider_id="test-auth-id-2",
    )

    db_session.add_all([user_1, user_2])
    await db_session.commit()

    db_session.add_all([
        Notification(
            user_id=user_1.id,
            type="MEETING_CREATED",
            message="Notification for user 1",
        ),
        Notification(
            user_id=user_2.id,
            type="MEETING_CREATED",
            message="Notification for user 2",
        ),
    ])

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=user_1.id,
        employee_id=employee_1.id,
        username="employee1",
        full_name="Employee 1",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/notifications")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["message"] == "Notification for user 1"


@pytest.mark.asyncio
async def test_notifications_are_ordered_by_newest_first(
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

    user = User(
        employee_id=employee.id,
        auth_provider_id="test-auth-id",
    )

    db_session.add(user)
    await db_session.commit()

    older = Notification(
        user_id=user.id,
        type="MEETING_CREATED",
        message="Older notification",
        created_at=datetime.now() - timedelta(minutes=10),
    )

    newer = Notification(
        user_id=user.id,
        type="MEETING_CREATED",
        message="Newer notification",
        created_at=datetime.now(),
    )

    db_session.add_all([older, newer])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=user.id,
        employee_id=employee.id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/notifications")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["message"] == "Newer notification"
    assert data[1]["message"] == "Older notification"