import pytest
from datetime import date, datetime
from app.models import Employee, Meeting, MeetingParticipant
from app.models.meeting import MeetingStatus
from app.models.meeting_participant import MeetingResponseStatus
from sqlalchemy.exc import IntegrityError

@pytest.mark.asyncio
async def test_meeting_can_be_created(db_session):
    organizer = Employee(
        username="meeting_model_organizer",
        full_name="Organizer",
        join_date=date.today(),
    )

    db_session.add(organizer)
    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
    )

    db_session.add(meeting)
    await db_session.flush()

    assert meeting.id is not None
    assert meeting.organizer_id == organizer.id
    assert meeting.status == MeetingStatus.SCHEDULED


@pytest.mark.asyncio
async def test_meeting_can_have_multiple_participants(db_session):
    organizer = Employee(
        username="meeting_model_org_multi",
        full_name="Organizer",
        join_date=date.today(),
    )

    participant1 = Employee(
        username="meeting_model_p1",
        full_name="Participant One",
        join_date=date.today(),
    )

    participant2 = Employee(
        username="meeting_model_p2",
        full_name="Participant Two",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant1,
        participant2,
    ])

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
    )

    meeting.participants.extend([
        MeetingParticipant(employee_id=participant1.id),
        MeetingParticipant(employee_id=participant2.id),
    ])

    db_session.add(meeting)
    await db_session.flush()

    assert len(meeting.participants) == 2

    assert {
        participant.employee_id
        for participant in meeting.participants
    } == {
        participant1.id,
        participant2.id,
    }


@pytest.mark.asyncio
async def test_meeting_participant_has_default_values(db_session):
    organizer = Employee(
        username="meeting_model_defaults_org",
        full_name="Organizer",
        join_date=date.today(),
    )

    participant = Employee(
        username="meeting_model_defaults_p",
        full_name="Participant",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant,
    ])

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
    )

    meeting_participant = MeetingParticipant(
        employee_id=participant.id,
    )

    meeting.participants.append(meeting_participant)

    db_session.add(meeting)
    await db_session.flush()

    assert meeting_participant.response_status == MeetingResponseStatus.PENDING
    assert meeting_participant.held_confirmed is False


@pytest.mark.asyncio
async def test_meeting_participant_belongs_to_employee_and_meeting(
    db_session,
):
    organizer = Employee(
        username="meeting_model_relation_org",
        full_name="Organizer",
        join_date=date.today(),
    )

    participant = Employee(
        username="meeting_model_relation_p",
        full_name="Participant",
        join_date=date.today(),
    )

    db_session.add_all([
        organizer,
        participant,
    ])

    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
    )

    meeting_participant = MeetingParticipant(
        employee_id=participant.id,
    )

    meeting.participants.append(meeting_participant)

    db_session.add(meeting)
    await db_session.flush()

    assert meeting_participant.meeting_id == meeting.id
    assert meeting_participant.employee_id == participant.id
    
@pytest.mark.asyncio
async def test_employee_cannot_be_added_twice_to_same_meeting(db_session):
    organizer = Employee(
        username="duplicate_org",
        full_name="Organizer",
        join_date=date.today(),
    )

    participant = Employee(
        username="duplicate_participant",
        full_name="Participant",
        join_date=date.today(),
    )

    db_session.add_all([organizer, participant])
    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
    )

    db_session.add(meeting)
    await db_session.flush()

    first = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=participant.id,
    )

    second = MeetingParticipant(
        meeting_id=meeting.id,
        employee_id=participant.id,
    )

    db_session.add(first)
    await db_session.flush()

    db_session.add(second)

    with pytest.raises(IntegrityError):
        await db_session.flush()