from datetime import date, datetime

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Employee
from app.models.meeting_participant import MeetingResponseStatus
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_organizer_is_auto_added_as_participant_when_not_included(
    client,
    db_session,
):
    manager = Employee(
        username="organizer_auto_add",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="organizer_auto_add_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="organizer_auto_add",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    create_response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [employee.id],
            "notes": "1:1",
        },
    )

    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    data = create_response.json()

    participant_ids = {p["employeeId"] for p in data["participants"]}
    assert manager.id in participant_ids
    assert employee.id in participant_ids

    manager_participant = next(
        p for p in data["participants"] if p["employeeId"] == manager.id
    )
    assert manager_participant["response"] == MeetingResponseStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_organizer_can_confirm_held_on_own_meeting_without_self_inviting(
    client,
    db_session,
):

    manager = Employee(
        username="organizer_confirm_held",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="organizer_confirm_held_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="organizer_confirm_held",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    create_response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [employee.id],
            "notes": "1:1",
        },
    )
    assert create_response.status_code == 201
    meeting_id = create_response.json()["id"]

    confirm_response = await client.post(
        f"/meetings/{meeting_id}/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )

    app.dependency_overrides.clear()

    assert confirm_response.status_code == 200
    manager_participant = next(
        p
        for p in confirm_response.json()["participants"]
        if p["employeeId"] == manager.id
    )
    assert manager_participant["confirmedHeld"] is True


@pytest.mark.asyncio
async def test_organizer_not_duplicated_when_already_self_invited(
    client,
    db_session,
):

    manager = Employee(
        username="organizer_no_dup",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="organizer_no_dup_target",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="organizer_no_dup",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    create_response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [employee.id, manager.id],
            "notes": "1:1",
        },
    )

    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    data = create_response.json()

    manager_rows = [
        p for p in data["participants"] if p["employeeId"] == manager.id
    ]
    assert len(manager_rows) == 1
    assert manager_rows[0]["response"] == MeetingResponseStatus.PENDING.value


@pytest.mark.asyncio
async def test_participant_employee_can_still_confirm_held_as_before(
    client,
    db_session,
):
    manager = Employee(
        username="regression_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    employee = Employee(
        username="regression_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="regression_manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    create_response = await client.post(
        "/meetings",
        json={
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [employee.id],
            "notes": "1:1",
        },
    )
    assert create_response.status_code == 201
    meeting_id = create_response.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=employee.id,
        username="regression_employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    confirm_response = await client.post(
        f"/meetings/{meeting_id}/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )

    app.dependency_overrides.clear()

    assert confirm_response.status_code == 200
