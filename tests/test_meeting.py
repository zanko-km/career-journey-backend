import pytest
from datetime import date, datetime, timedelta

from app.models import (
    Employee,
    Meeting,
    MeetingParticipant,
    MeetingStatus,
    Department,
    Team,
    HrbpTeamAssignment,
)
from app.core.current_user import AuthenticatedUser
from app.main import app
from app.core.current_user import get_current_user
from app.models.user import EmployeeRoleType
from app.models.meeting_participant import MeetingResponseStatus


@pytest.mark.asyncio
async def test_employee_can_see_own_meetings(
    client,
    db_session,
):
    employee = Employee(
        username="meeting_employee",
        full_name="Meeting Employee",
        join_date=date.today(),
    )

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add(meeting)
    await db_session.flush()

    participant = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=employee.id,
    )

    db_session.add(participant)
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


    response = await client.get("/meetings")

    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0]["id"] == meeting.id

    assert data[0]["organizerId"] == organizer.id

    assert data[0]["participants"][0]["employeeId"] == employee.id

    assert data[0]["participants"][0]["response"] == "PENDING"

    assert data[0]["participants"][0]["confirmedHeld"] is False
    
    
@pytest.mark.asyncio
async def test_employee_cannot_see_other_employee_meetings(
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

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee1,
            employee2,
            organizer,
        ]
    )

    await db_session.flush()

    visible_meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    hidden_meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add_all(
        [
            visible_meeting,
            hidden_meeting,
        ]
    )

    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=visible_meeting.id,
            employee_id=employee1.id,
        )
    )

    db_session.add(
        MeetingParticipant(
            meeting_id=hidden_meeting.id,
            employee_id=employee2.id,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee1.id,
        username="employee1",
        full_name="Employee 1",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == visible_meeting.id
    
    
@pytest.mark.asyncio
async def test_list_meetings_without_token_returns_401(
    client,
):
    response = await client.get("/meetings")

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_manager_can_see_team_meetings(
    client,
    db_session,
):
    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )

    db_session.add(manager)

    await db_session.flush()


    employee = Employee(
        username="team_employee",
        full_name="Team Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add(meeting)

    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee.id,
        )
    )

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

    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == meeting.id
    
    
@pytest.mark.asyncio
async def test_manager_cannot_see_other_team_meetings(
    client,
    db_session,
):
    manager1 = Employee(
        username="manager1",
        full_name="Manager 1",
        join_date=date.today(),
    )

    manager2 = Employee(
        username="manager2",
        full_name="Manager 2",
        join_date=date.today(),
    )

    employee2 = Employee(
        username="employee2",
        full_name="Employee 2",
        join_date=date.today(),
        manager_id=manager2.id,
    )

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            manager1,
            manager2,
            employee2,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add(meeting)

    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee2.id,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager1.id,
        username="manager1",
        full_name="Manager 1",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 0
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_see_all_meetings(
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

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee1,
            employee2,
            organizer,
        ]
    )

    await db_session.flush()

    meeting1 = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    meeting2 = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add_all(
        [
            meeting1,
            meeting2,
        ]
    )

    await db_session.flush()

    db_session.add_all(
        [
            MeetingParticipant(
                meeting_id=meeting1.id,
                employee_id=employee1.id,
            ),
            MeetingParticipant(
                meeting_id=meeting2.id,
                employee_id=employee2.id,
            ),
        ]
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=organizer.id,
        username="hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )

    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 2
    
    
@pytest.mark.asyncio
async def test_hrbp_can_see_scoped_meetings(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )

    manager = Employee(
        username="team_manager",
        full_name="Team Manager",
        join_date=date.today(),
    )

    employee = Employee(
        username="hrbp_employee",
        full_name="HRBP Employee",
        join_date=date.today(),
    )

    other_employee = Employee(
        username="other_employee",
        full_name="Other Employee",
        join_date=date.today(),
    )

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            hrbp,
            manager,
            employee,
            other_employee,
            organizer,
        ]
    )

    await db_session.flush()


    department = Department(
        name="Engineering",
    )

    db_session.add(department)
    await db_session.flush()


    team = Team(
        name="Backend Team",
        department_id=department.id,
        team_manager_id=manager.id,
    )

    db_session.add(team)
    await db_session.flush()


    employee.team_id = team.id


    db_session.add(
        HrbpTeamAssignment(
            hrbp_id=hrbp.id,
            team_id=team.id,
        )
    )


    visible_meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    hidden_meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.SCHEDULED,
    )

    db_session.add_all(
        [
            visible_meeting,
            hidden_meeting,
        ]
    )

    await db_session.flush()


    db_session.add(
        MeetingParticipant(
            meeting_id=visible_meeting.id,
            employee_id=employee.id,
        )
    )


    db_session.add(
        MeetingParticipant(
            meeting_id=hidden_meeting.id,
            employee_id=other_employee.id,
        )
    )


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


    response = await client.get("/meetings")


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    assert data[0]["id"] == visible_meeting.id
    
    
@pytest.mark.asyncio
async def test_manager_can_create_meeting(
    client,
    db_session,
):
    manager = Employee(
        username="manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)

    await db_session.flush()
    employee = Employee(
        username="employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )

    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()

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
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [
                employee.id
            ],
            "notes": "first meeting"
        }
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201

    data = response.json()

    assert data["employeeId"] == employee.id
    assert data["status"] == "PROPOSED"
    
@pytest.mark.asyncio
async def test_create_meeting_without_token_returns_401(client):
    response = await client.post(
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": 1,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [1],
            "notes": "meeting",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_cannot_create_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="employee_create",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_create",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )

    response = await client.post(
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [employee.id],
            "notes": "meeting",
        },
    )

    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_hrbp_can_create_meeting(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_create",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_target",
        full_name="Employee Target",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            hrbp,
            employee,
        ]
    )

    await db_session.flush()

    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_create",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.post(
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [
                employee.id
            ],
            "notes": "meeting",
        },
    )


    assert response.status_code == 201
    
    
@pytest.mark.asyncio
async def test_hr_manager_can_create_meeting(
    client,
    db_session,
):
    hr_manager = Employee(
        username="hr_manager_create",
        full_name="HR Manager",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_hr",
        full_name="Employee",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            hr_manager,
            employee,
        ]
    )

    await db_session.flush()


    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hr_manager.id,
        username="hr_manager_create",
        full_name="HR Manager",
        roles=[
            EmployeeRoleType.HR_MANAGER
        ],
    )


    response = await client.post(
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds": [
                employee.id
            ],
            "notes": "meeting",
        },
    )


    assert response.status_code == 201
    
    
@pytest.mark.asyncio
async def test_manager_cannot_create_meeting_for_outside_employee(
    client,
    db_session,
):
    manager = Employee(
        username="manager_scope",
        full_name="Manager",
        join_date=date.today(),
    )

    employee = Employee(
        username="outside_employee",
        full_name="Outside",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            manager,
            employee,
        ]
    )

    await db_session.flush()


    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=manager.id,
        username="manager_scope",
        full_name="Manager",
        roles=[
            EmployeeRoleType.MANAGER
        ],
    )


    response = await client.post(
        "/meetings",
        json={
            "type": "ONBOARDING_MONTH_1",
            "employeeId": employee.id,
            "scheduledAt": datetime.now().isoformat(),
            "participantIds":[employee.id],
            "notes":"meeting",
        },
    )


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_create_meeting_employee_not_found(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_not_found",
        full_name="HRBP",
        join_date=date.today(),
    )

    db_session.add(hrbp)
    await db_session.flush()


    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_not_found",
        full_name="HRBP",
        roles=[
            EmployeeRoleType.HRBP
        ],
    )


    response = await client.post(
        "/meetings",
        json={
            "type":"ONBOARDING_MONTH_1",
            "employeeId":999999,
            "scheduledAt":datetime.now().isoformat(),
            "participantIds":[999999],
            "notes":"meeting",
        },
    )


    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_create_meeting_with_past_datetime_returns_422(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_past",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_past",
        full_name="Employee",
        join_date=date.today(),
    )


    db_session.add_all([hrbp, employee])
    await db_session.flush()


    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_past",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


    response = await client.post(
        "/meetings",
        json={
            "type":"ONBOARDING_MONTH_1",
            "employeeId":employee.id,
            "scheduledAt":(
                datetime.now() - timedelta(days=1)
            ).isoformat(),
            "participantIds":[employee.id],
        },
    )


    assert response.status_code == 422
    
    
@pytest.mark.asyncio
async def test_create_meeting_with_duplicate_participants_returns_422(
    client,
    db_session,
):
    hrbp = Employee(
        username="hrbp_dup",
        full_name="HRBP",
        join_date=date.today(),
    )

    employee = Employee(
        username="employee_dup",
        full_name="Employee",
        join_date=date.today(),
    )


    db_session.add_all([hrbp, employee])
    await db_session.flush()


    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="hrbp_dup",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP],
    )


    response = await client.post(
        "/meetings",
        json={
            "type":"ONBOARDING_MONTH_1",
            "employeeId":employee.id,
            "scheduledAt":datetime.now().isoformat(),
            "participantIds":[
                employee.id,
                employee.id,
            ],
        },
    )


    assert response.status_code == 422
    
    
@pytest.mark.asyncio
async def test_participant_can_get_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="employee_get",
        full_name="Employee",
        join_date=date.today(),
    )

    organizer = Employee(
        username="manager_get",
        full_name="Manager",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()


    meeting = Meeting(
        employee_id=employee.id,
        organizer_id=organizer.id,
        scheduled_at=datetime.now()+timedelta(days=1),
        status=MeetingStatus.PROPOSED,
        notes="test",
    )

    db_session.add(meeting)
    await db_session.flush()


    participant = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=employee.id,
    )

    db_session.add(participant)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="employee_get",
        full_name="Employee",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.get(
        f"/meetings/{meeting.id}"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200
    assert response.json()["id"] == meeting.id
    
    
@pytest.mark.asyncio
async def test_get_meeting_without_token_returns_401(
    client,
):

    response = await client.get(
        "/meetings/1"
    )

    assert response.status_code == 401
    
    
@pytest.mark.asyncio
async def test_employee_cannot_get_other_meeting(
    client,
    db_session,
):

    owner = Employee(
        username="owner",
        full_name="Owner",
        join_date=date.today(),
    )

    other = Employee(
        username="other",
        full_name="Other",
        join_date=date.today(),
    )

    organizer = Employee(
        username="org",
        full_name="Org",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            owner,
            other,
            organizer,
        ]
    )

    await db_session.flush()


    meeting = Meeting(
        employee_id=owner.id,
        organizer_id=organizer.id,
        scheduled_at=datetime.now()+timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )


    db_session.add(meeting)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=other.id,
        username="other",
        full_name="Other",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.get(
        f"/meetings/{meeting.id}"
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_participant_can_confirm_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="participant",
        full_name="Participant",
        join_date=date.today(),
    )

    organizer = Employee(
        username="organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()

    participant = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=employee.id,
        response_status=MeetingResponseStatus.PENDING,
    )

    db_session.add(participant)
    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="participant",
        full_name="Participant",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/meetings/{meeting.id}/respond",
        json={
            "response": "CONFIRMED"
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200

    data = response.json()

    assert data["participants"][0]["response"] == "CONFIRMED"
    
    
@pytest.mark.asyncio
async def test_participant_can_reject_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="participant_reject",
        full_name="Participant",
        join_date=date.today(),
    )

    organizer = Employee(
        username="organizer_reject",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()


    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()


    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee.id,
            response_status=MeetingResponseStatus.PENDING,
        )
    )

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="participant_reject",
        full_name="Participant",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/meetings/{meeting.id}/respond",
        json={
            "response": "REJECTED"
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 200
    
    
@pytest.mark.asyncio
async def test_non_participant_cannot_respond_to_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="real_participant",
        full_name="Real",
        join_date=date.today(),
    )

    other = Employee(
        username="other_user",
        full_name="Other",
        join_date=date.today(),
    )

    organizer = Employee(
        username="organizer2",
        full_name="Organizer",
        join_date=date.today(),
    )


    db_session.add_all(
        [
            employee,
            other,
            organizer,
        ]
    )

    await db_session.flush()


    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()


    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee.id,
        )
    )

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=other.id,
        username="other_user",
        full_name="Other",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/meetings/{meeting.id}/respond",
        json={
            "response": "CONFIRMED"
        },
    )


    app.dependency_overrides.clear()


    assert response.status_code == 403
    
    
@pytest.mark.asyncio
async def test_participant_can_confirm_held_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="held_participant",
        full_name="Held Participant",
        join_date=date.today(),
    )

    organizer = Employee(
        username="held_organizer",
        full_name="Held Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()

    participant = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=employee.id,
        response_status=MeetingResponseStatus.CONFIRMED,
    )

    db_session.add(participant)

    await db_session.commit()


    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="held_participant",
        full_name="Held Participant",
        roles=[
            EmployeeRoleType.EMPLOYEE
        ],
    )


    response = await client.post(
        f"/meetings/{meeting.id}/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )


    assert response.status_code == 200

    data = response.json()

    assert data["participants"][0]["confirmedHeld"] is True
    assert (
        data["participants"][0]["allRequiredParticipantsPresent"]
        is True
    )
    
    
@pytest.mark.asyncio
async def test_participant_can_confirm_meeting_not_held(
    client,
    db_session,
):
    employee = Employee(
        username="not_held_participant",
        full_name="Not Held Participant",
        join_date=date.today(),
    )

    organizer = Employee(
        username="not_held_organizer",
        full_name="Not Held Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee.id,
            response_status=MeetingResponseStatus.CONFIRMED,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="not_held_participant",
        full_name="Not Held Participant",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/meetings/{meeting.id}/confirm-held",
        json={
            "held": False,
            "allRequiredParticipantsPresent": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["participants"][0]["confirmedHeld"] is False
    assert data["participants"][0]["allRequiredParticipantsPresent"] is False
    
    
@pytest.mark.asyncio
async def test_non_participant_cannot_confirm_held_meeting(
    client,
    db_session,
):
    employee = Employee(
        username="not_participant",
        full_name="Not Participant",
        join_date=date.today(),
    )

    participant = Employee(
        username="real_participant",
        full_name="Real Participant",
        join_date=date.today(),
    )

    organizer = Employee(
        username="confirm_organizer",
        full_name="Confirm Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            participant,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=participant.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=participant.id,
            response_status=MeetingResponseStatus.CONFIRMED,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="not_participant",
        full_name="Not Participant",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        f"/meetings/{meeting.id}/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )

    assert response.status_code == 403
    
@pytest.mark.asyncio
async def test_confirm_held_meeting_without_token_returns_401(
    client,
):
    response = await client.post(
        "/meetings/1/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )

    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_confirm_held_meeting_not_found(
    client,
    db_session,
):
    employee = Employee(
        username="missing_meeting_user",
        full_name="Missing Meeting User",
        join_date=date.today(),
    )

    db_session.add(employee)

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="missing_meeting_user",
        full_name="Missing Meeting User",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.post(
        "/meetings/999999/confirm-held",
        json={
            "held": True,
            "allRequiredParticipantsPresent": True,
        },
    )

    assert response.status_code == 404
    
    
@pytest.mark.asyncio
async def test_participant_cannot_confirm_held_meeting_twice(
    client,
    db_session,
):
    employee = Employee(
        username="double_confirm",
        full_name="Double Confirm",
        join_date=date.today(),
    )

    organizer = Employee(
        username="double_confirm_org",
        full_name="Double Confirm Organizer",
        join_date=date.today(),
    )

    db_session.add_all(
        [
            employee,
            organizer,
        ]
    )

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=1),
        status=MeetingStatus.PROPOSED,
    )

    db_session.add(meeting)
    await db_session.flush()

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=employee.id,
            response_status=MeetingResponseStatus.CONFIRMED,
        )
    )

    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="double_confirm",
        full_name="Double Confirm",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    payload = {
        "held": True,
        "allRequiredParticipantsPresent": True,
    }

    first_response = await client.post(
        f"/meetings/{meeting.id}/confirm-held",
        json=payload,
    )

    assert first_response.status_code == 200

    second_response = await client.post(
        f"/meetings/{meeting.id}/confirm-held",
        json=payload,
    )

    assert second_response.status_code == 409
    
    
@pytest.mark.asyncio
async def test_confirm_held_meeting_invalid_payload_returns_422(
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
        "/meetings/1/confirm-held",
        json={
            "allRequiredParticipantsPresent": True,
        },
    )

    assert response.status_code == 422