import pytest
from datetime import date, datetime

from app.main import app
from app.core.current_user import get_current_user, AuthenticatedUser
from app.models import (
    Employee,
    Onboarding,
    OnboardingStatus,
    Meeting,
    MeetingParticipant,
    MeetingStatus,
)
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_hrbp_can_complete_month1_and_start_month2(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_user",
        full_name="HRBP User",
        join_date=date.today(),
    )

    manager = Employee(
        username="manager_user",
        full_name="Manager User",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_user",
        full_name="Employee User",
        join_date=date.today(),
        manager_id=None,
    )

    db_session.add_all([
        hrbp,
        manager,
        employee,
    ])

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

    await db_session.flush()

    meeting = Meeting(
        organizer_id=hrbp.id,
        onboarding_id=onboarding.id,
        onboarding_month=1,
        scheduled_at=datetime.now(),
        notes="HRBP month 1 meeting completed",
    )

    db_session.add(meeting)

    await db_session.flush()

    participant = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=hrbp.id,
        held_confirmed=True,
    )

    db_session.add(participant)

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )

    response = await client.post(
        f"/employees/{employee.id}/onboarding/notify-manager-after-hrbp"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["employeeId"] == employee.id
    assert data["currentPhaseNumber"] == 2
    assert data["status"] == "IN_PROGRESS"
    

@pytest.mark.asyncio
async def test_notify_manager_fails_when_onboarding_not_found(
    client,
):

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
        "/employees/999/onboarding/notify-manager-after-hrbp"
    )


    assert response.status_code == 404



@pytest.mark.asyncio
async def test_employee_cannot_call_notify_manager(
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
        "/employees/1/onboarding/notify-manager-after-hrbp"
    )


    assert response.status_code == 403



@pytest.mark.asyncio
async def test_hrbp_cannot_repeat_manager_notification(
    client,
    db_session,
):

    employee = Employee(
        username="repeat_employee",
        full_name="Repeat Employee",
        join_date=date.today(),
    )


    db_session.add(employee)
    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=2,
        status=OnboardingStatus.IN_PROGRESS,
    )

    db_session.add(onboarding)

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
        f"/employees/{employee.id}/onboarding/notify-manager-after-hrbp"
    )


    assert response.status_code == 409


@pytest.mark.asyncio
async def test_notify_manager_requires_auth(client):
    app.dependency_overrides.clear()

    response = await client.post(
        "/employees/1/onboarding/notify-manager-after-hrbp"
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_notify_manager_fails_without_hrbp_meeting(
    client,
    db_session,
):

    hrbp = Employee(
        username="hrbp_no_meeting",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_no_meeting",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add_all([
        hrbp,
        employee,
    ])

    await db_session.flush()

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
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/notify-manager-after-hrbp"
    )


    assert response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_notify_manager_fails_without_meeting_notes(
    client,
    db_session,
):

    hrbp = Employee(
        username="hrbp_no_notes",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_no_notes",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add_all([
        hrbp,
        employee,
    ])

    await db_session.flush()


    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
        current_phase_number=1,
        status=OnboardingStatus.IN_PROGRESS,
    )

    db_session.add(onboarding)

    await db_session.flush()


    meeting = Meeting(
        organizer_id=hrbp.id,
        onboarding_id=onboarding.id,
        onboarding_month=1,
        scheduled_at=datetime.now(),
        status=MeetingStatus.HELD,
        notes="",
    )


    meeting.participants.append(
        MeetingParticipant(
            employee_id=hrbp.id,
            held_confirmed=True,
        )
    )

    meeting.participants.append(
        MeetingParticipant(
            employee_id=employee.id,
            held_confirmed=True,
        )
    )


    db_session.add(meeting)

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.post(
        f"/employees/{employee.id}/onboarding/notify-manager-after-hrbp"
    )


    assert response.status_code == 409