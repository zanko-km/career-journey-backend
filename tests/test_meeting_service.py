import pytest
from datetime import date, datetime
from app.models import Employee
from app.services.meeting import MeetingService


@pytest.mark.asyncio
async def test_meeting_lifecycle_schedule_confirm_hold(db_session):
    organizer = Employee(username="hrbp2", full_name="HRBP Two", join_date=date.today())
    participant = Employee(username="emp2", full_name="Employee Two", join_date=date.today())
    db_session.add_all([organizer, participant])
    await db_session.flush()

    service = MeetingService(db_session)
    meeting = await service.schedule(organizer.id, participant.id, datetime.now())

    confirmed = await service.confirm(meeting.id)
    assert confirmed.status.value == "CONFIRMED"

    held = await service.mark_held(meeting.id)
    assert held.status.value == "HELD"


@pytest.mark.asyncio
async def test_cannot_confirm_twice(db_session):
    organizer = Employee(username="hrbp3", full_name="HRBP Three", join_date=date.today())
    participant = Employee(username="emp3", full_name="Employee Three", join_date=date.today())
    db_session.add_all([organizer, participant])
    await db_session.flush()

    service = MeetingService(db_session)
    meeting = await service.schedule(organizer.id, participant.id, datetime.now())
    await service.confirm(meeting.id)

    with pytest.raises(ValueError):
        await service.confirm(meeting.id)