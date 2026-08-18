from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meeting, MeetingStatus


class MeetingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule(
        self,
        organizer_id: int,
        participant_id: int,
        scheduled_at: datetime,
        onboarding_id: int | None = None,
        onboarding_month: int | None = None,
    ) -> Meeting:
        meeting = Meeting(
            organizer_id=organizer_id,
            participant_id=participant_id,
            scheduled_at=scheduled_at,
            onboarding_id=onboarding_id,
            onboarding_month=onboarding_month,
        )
        self.db.add(meeting)
        await self.db.flush()
        return meeting

    async def _get(self, meeting_id: int) -> Meeting:
        meeting = await self.db.get(Meeting, meeting_id)
        if meeting is None:
            raise ValueError("Meeting not found")
        return meeting

    async def confirm(self, meeting_id: int) -> Meeting:
        meeting = await self._get(meeting_id)
        if meeting.status != MeetingStatus.SCHEDULED:
            raise ValueError(f"Cannot confirm meeting in status {meeting.status}")
        meeting.status = MeetingStatus.CONFIRMED
        await self.db.flush()
        return meeting

    async def mark_held(self, meeting_id: int) -> Meeting:
        meeting = await self._get(meeting_id)
        if meeting.status != MeetingStatus.CONFIRMED:
            raise ValueError(f"Cannot mark held from status {meeting.status}")
        meeting.status = MeetingStatus.HELD
        await self.db.flush()
        return meeting