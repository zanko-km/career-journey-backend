from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.models import Employee, Meeting, MeetingParticipant, MeetingStatus
from app.services.meeting import MeetingService


async def _make_meeting(db_session, status: MeetingStatus) -> Meeting:
    organizer = Employee(username=f"organizer_{status.value}", full_name="Organizer", join_date=date.today())
    attendee = Employee(username=f"attendee_{status.value}", full_name="Attendee", join_date=date.today())
    db_session.add_all([organizer, attendee])
    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=status,
    )
    meeting.participants.append(MeetingParticipant(employee_id=attendee.id))
    db_session.add(meeting)
    await db_session.flush()

    return meeting


ALL_STATUSES = list(MeetingStatus)
NON_SCHEDULED_STATUSES = [s for s in ALL_STATUSES if s != MeetingStatus.SCHEDULED]
NON_CONFIRMED_STATUSES = [s for s in ALL_STATUSES if s != MeetingStatus.CONFIRMED]


@pytest.mark.asyncio
async def test_schedule_always_creates_a_scheduled_meeting(db_session):
    organizer = Employee(username="org1", full_name="Organizer", join_date=date.today())
    attendee = Employee(username="att1", full_name="Attendee", join_date=date.today())
    db_session.add_all([organizer, attendee])
    await db_session.flush()

    service = MeetingService(db_session)
    meeting = await service.schedule(
        organizer_id=organizer.id,
        participant_ids=[attendee.id],
        scheduled_at=datetime.now(),
    )

    assert meeting.status == MeetingStatus.SCHEDULED


@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_SCHEDULED_STATUSES)
async def test_confirm_rejected_from_every_non_scheduled_status(db_session, status):
    meeting = await _make_meeting(db_session, status)
    service = MeetingService(db_session)

    with pytest.raises(ValueError, match="Cannot confirm meeting"):
        await service.confirm(meeting.id)

    # status must be untouched after a rejected transition
    await db_session.refresh(meeting)
    assert meeting.status == status


@pytest.mark.asyncio
async def test_confirm_accepted_from_scheduled(db_session):
    meeting = await _make_meeting(db_session, MeetingStatus.SCHEDULED)
    service = MeetingService(db_session)

    updated = await service.confirm(meeting.id)

    assert updated.status == MeetingStatus.CONFIRMED


@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_CONFIRMED_STATUSES)
async def test_mark_held_rejected_from_every_non_confirmed_status(db_session, status):
    meeting = await _make_meeting(db_session, status)
    service = MeetingService(db_session)

    participant = (await db_session.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting.id
        )
    )).scalars().first()

    with pytest.raises(ValueError, match="Cannot mark held"):
        await service.mark_held(meeting.id, participant.employee_id)

    await db_session.refresh(meeting)
    assert meeting.status == status


@pytest.mark.asyncio
async def test_mark_held_requires_every_participant_to_confirm(db_session):
    """Partial confirmation must NOT flip the meeting to HELD."""
    organizer = Employee(username="org2", full_name="Organizer", join_date=date.today())
    p1 = Employee(username="p1", full_name="Participant 1", join_date=date.today())
    p2 = Employee(username="p2", full_name="Participant 2", join_date=date.today())
    db_session.add_all([organizer, p1, p2])
    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        scheduled_at=datetime.now(),
        status=MeetingStatus.CONFIRMED,
    )
    meeting.participants.append(MeetingParticipant(employee_id=p1.id))
    meeting.participants.append(MeetingParticipant(employee_id=p2.id))
    db_session.add(meeting)
    await db_session.flush()

    service = MeetingService(db_session)

    # Only p1 confirms attendance -> meeting must stay CONFIRMED
    await service.mark_held(meeting.id, p1.id)
    await db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.CONFIRMED

    # p2 confirms too -> meeting flips to HELD
    await service.mark_held(meeting.id, p2.id)
    await db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.HELD


@pytest.mark.asyncio
async def test_mark_held_rejects_unknown_participant(db_session):
    meeting = await _make_meeting(db_session, MeetingStatus.CONFIRMED)
    outsider = Employee(username="outsider", full_name="Outsider", join_date=date.today())
    db_session.add(outsider)
    await db_session.flush()

    service = MeetingService(db_session)

    with pytest.raises(ValueError, match="not a participant"):
        await service.mark_held(meeting.id, outsider.id)
