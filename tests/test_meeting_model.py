import pytest
from datetime import date, datetime
from app.models import Employee, Meeting


@pytest.mark.asyncio
async def test_meeting_can_be_created(db_session):
    organizer = Employee(username="hrbp1", full_name="HRBP One", join_date=date.today())
    participant = Employee(username="emp1", full_name="Employee One", join_date=date.today())
    db_session.add_all([organizer, participant])
    await db_session.flush()

    meeting = Meeting(
        organizer_id=organizer.id,
        participant_id=participant.id,
        scheduled_at=datetime.now(),
    )
    db_session.add(meeting)
    await db_session.flush()

    assert meeting.status.value == "SCHEDULED"