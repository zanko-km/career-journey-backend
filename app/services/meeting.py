from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Meeting,
    MeetingParticipant,
    MeetingStatus,
)
from app.models.meeting_participant import MeetingResponseStatus


class MeetingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule(
        self,
        organizer_id: int,
        participant_ids: list[int],
        scheduled_at: datetime,
        onboarding_id: int | None = None,
        onboarding_month: int | None = None,
    ) -> Meeting:
        meeting = Meeting(
            organizer_id=organizer_id,
            scheduled_at=scheduled_at,
            onboarding_id=onboarding_id,
            onboarding_month=onboarding_month,
            status = MeetingStatus.SCHEDULED
        )

        for employee_id in participant_ids:
            meeting.participants.append(
                MeetingParticipant(
                    employee_id=employee_id,
                )
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
            raise ValueError(
                f"Cannot confirm meeting in status {meeting.status}"
            )

        meeting.status = MeetingStatus.CONFIRMED

        await self.db.flush()

        return meeting

    async def respond(
        self,
        meeting_id: int,
        employee_id: int,
        response: MeetingResponseStatus,
    ) -> MeetingParticipant:
        result = await self.db.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.employee_id == employee_id,
            )
        )

        participant = result.scalar_one_or_none()

        if participant is None:
            raise ValueError(
                "Employee is not a participant of this meeting"
            )

        participant.response_status = response

        await self.db.flush()

        return participant

    async def mark_held(
        self,
        meeting_id: int,
        employee_id: int,
    ) -> MeetingParticipant:
        meeting = await self._get(meeting_id)

        if meeting.status != MeetingStatus.CONFIRMED:
            raise ValueError(
                f"Cannot mark held from status {meeting.status}"
            )

        result = await self.db.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.employee_id == employee_id,
            )
        )

        participant = result.scalar_one_or_none()

        if participant is None:
            raise ValueError(
                "Employee is not a participant of this meeting"
            )

        participant.held_confirmed = True

        result = await self.db.execute(
            select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_id
            )
        )

        participants = result.scalars().all()

        if all(
            participant.held_confirmed
            for participant in participants
        ):
            meeting.status = MeetingStatus.HELD

        await self.db.flush()

        return participant
    
    
    async def get_visible_meetings(
        self,
        employee_id: int,
    ) -> list[Meeting]:

        result = await self.db.execute(
            select(Meeting)
            .outerjoin(
                MeetingParticipant,
                MeetingParticipant.meeting_id == Meeting.id,
            )
            .where(
                or_(
                    Meeting.organizer_id == employee_id,
                    MeetingParticipant.employee_id == employee_id,
                )
            )
        )

        return result.scalars().unique().all()