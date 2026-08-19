import pytest
from app.models import Employee
from app.services.meeting import MeetingService
from datetime import date, datetime
from app.models.meeting_participant import MeetingResponseStatus

@pytest.mark.asyncio
async def test_meeting_lifecycle_schedule_confirm_hold(db_session):
    organizer = Employee(
        username="hrbp2",
        full_name="HRBP Two",
        join_date=date.today(),
    )
    participant = Employee(
        username="emp2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    db_session.add_all([organizer, participant])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant.id],
        datetime.now(),
    )

    confirmed = await service.confirm(meeting.id)
    assert confirmed.status.value == "CONFIRMED"

    held = await service.mark_held(
        meeting.id,
        participant.id,
    )

    assert held.held_confirmed is True


@pytest.mark.asyncio
async def test_cannot_confirm_twice(db_session):
    organizer = Employee(username="hrbp3", full_name="HRBP Three", join_date=date.today())
    participant = Employee(username="emp3", full_name="Employee Three", join_date=date.today())
    db_session.add_all([organizer, participant])
    await db_session.flush()

    service = MeetingService(db_session)
    meeting = await service.schedule(
        organizer.id,
        [participant.id],
        datetime.now(),
    )
    await service.confirm(meeting.id)

    with pytest.raises(ValueError):
        await service.confirm(meeting.id)
        


@pytest.mark.asyncio
async def test_schedule_meeting_with_multiple_participants(db_session):
    organizer = Employee(
        username="hrbp2",
        full_name="HRBP Two",
        join_date=date.today(),
    )

    participant1 = Employee(
        username="emp2",
        full_name="Employee Two",
        join_date=date.today(),
    )

    participant2 = Employee(
        username="emp3",
        full_name="Employee Three",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant1,
        participant2,
    ])

    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer_id=organizer.id,
        participant_ids=[
            participant1.id,
            participant2.id,
        ],
        scheduled_at=datetime.now(),
    )

    assert len(meeting.participants) == 2

    participant_ids = {
        participant.employee_id
        for participant in meeting.participants
    }

    assert participant_ids == {
        participant1.id,
        participant2.id,
    }


@pytest.mark.asyncio
async def test_participant_can_respond_to_meeting(db_session):
    organizer = Employee(
        username="hrbp4",
        full_name="HRBP Four",
        join_date=date.today(),
    )

    participant = Employee(
        username="emp4",
        full_name="Employee Four",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant,
    ])

    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer_id=organizer.id,
        participant_ids=[participant.id],
        scheduled_at=datetime.now(),
    )

    updated = await service.respond(
        meeting.id,
        participant.id,
        MeetingResponseStatus.ACCEPTED,
    )

    assert updated.response_status == MeetingResponseStatus.ACCEPTED


@pytest.mark.asyncio
async def test_participant_can_mark_meeting_held(db_session):
    organizer = Employee(
        username="hrbp5",
        full_name="HRBP Five",
        join_date=date.today(),
    )

    participant = Employee(
        username="emp5",
        full_name="Employee Five",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant,
    ])

    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant.id],
        datetime.now(),
    )

    await service.confirm(meeting.id)

    updated = await service.mark_held(
        meeting.id,
        participant.id,
    )

    assert updated.held_confirmed is True
    
@pytest.mark.asyncio
async def test_schedule_meeting_with_multiple_participants(db_session):
    organizer = Employee(
        username="organizer_multi",
        full_name="Organizer",
        join_date=date.today(),
    )
    participant1 = Employee(
        username="participant_multi_1",
        full_name="Participant One",
        join_date=date.today(),
    )
    participant2 = Employee(
        username="participant_multi_2",
        full_name="Participant Two",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant1,
        participant2,
    ])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant1.id, participant2.id],
        datetime.now(),
    )

    assert meeting.organizer_id == organizer.id
    assert len(meeting.participants) == 2

    participant_ids = {
        participant.employee_id
        for participant in meeting.participants
    }

    assert participant_ids == {
        participant1.id,
        participant2.id,
    }
    
@pytest.mark.asyncio
async def test_participant_can_respond_to_meeting(db_session):
    organizer = Employee(
        username="organizer_response",
        full_name="Organizer",
        join_date=date.today(),
    )
    participant = Employee(
        username="participant_response",
        full_name="Participant",
        join_date=date.today(),
    )

    db_session.add_all([organizer, participant])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant.id],
        datetime.now(),
    )

    response = await service.respond(
        meeting.id,
        participant.id,
        "ACCEPTED",
    )

    assert response.employee_id == participant.id
    assert response.response_status == "ACCEPTED"
    
@pytest.mark.asyncio
async def test_participants_have_independent_response_status(db_session):
    organizer = Employee(
        username="organizer_independent",
        full_name="Organizer",
        join_date=date.today(),
    )
    participant1 = Employee(
        username="participant_independent_1",
        full_name="Participant One",
        join_date=date.today(),
    )
    participant2 = Employee(
        username="participant_independent_2",
        full_name="Participant Two",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant1,
        participant2,
    ])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant1.id, participant2.id],
        datetime.now(),
    )

    await service.respond(
        meeting.id,
        participant1.id,
        "ACCEPTED",
    )

    participant2_response = await service.respond(
        meeting.id,
        participant2.id,
        "DECLINED",
    )

    assert participant2_response.employee_id == participant2.id
    assert participant2_response.response_status == "DECLINED"
    
@pytest.mark.asyncio
async def test_meeting_becomes_held_only_when_all_participants_confirm(db_session):
    organizer = Employee(
        username="organizer_held",
        full_name="Organizer",
        join_date=date.today(),
    )
    participant1 = Employee(
        username="participant_held_1",
        full_name="Participant One",
        join_date=date.today(),
    )
    participant2 = Employee(
        username="participant_held_2",
        full_name="Participant Two",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant1,
        participant2,
    ])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant1.id, participant2.id],
        datetime.now(),
    )

    await service.confirm(meeting.id)

    await service.mark_held(
        meeting.id,
        participant1.id,
    )

    assert meeting.status.value == "CONFIRMED"

    await service.mark_held(
        meeting.id,
        participant2.id,
    )

    assert meeting.status.value == "HELD"
    
@pytest.mark.asyncio
async def test_mark_held_rejects_non_participant(db_session):
    organizer = Employee(
        username="organizer_invalid",
        full_name="Organizer",
        join_date=date.today(),
    )
    participant = Employee(
        username="participant_invalid",
        full_name="Participant",
        join_date=date.today(),
    )
    outsider = Employee(
        username="outsider_invalid",
        full_name="Outsider",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant,
        outsider,
    ])
    await db_session.flush()

    service = MeetingService(db_session)

    meeting = await service.schedule(
        organizer.id,
        [participant.id],
        datetime.now(),
    )

    await service.confirm(meeting.id)

    with pytest.raises(ValueError):
        await service.mark_held(
            meeting.id,
            outsider.id,
        )