from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Onboarding, OnboardingStatus
from app.models import Meeting, MeetingStatus

NEXT_STATUS = {
    OnboardingStatus.MONTH_1: OnboardingStatus.MONTH_2,
    OnboardingStatus.MONTH_2: OnboardingStatus.MONTH_3,
}
STATUS_TO_MONTH = {
    OnboardingStatus.MONTH_1: 1,
    OnboardingStatus.MONTH_2: 2,
    OnboardingStatus.MONTH_3: 3,
}

class OnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_onboarding(self, employee_id: int, start_date: date) -> Onboarding:
        onboarding = Onboarding(
            employee_id=employee_id,
            start_date=start_date,
            status=OnboardingStatus.MONTH_1,
        )
        self.db.add(onboarding)
        await self.db.flush()
        return onboarding

    async def _get(self, onboarding_id: int) -> Onboarding:
        onboarding = await self.db.get(Onboarding, onboarding_id)
        if onboarding is None:
            raise ValueError("Onboarding not found")
        return onboarding

    async def advance_to_next_month(self, onboarding_id: int) -> Onboarding:
        onboarding = await self._get(onboarding_id)

        if onboarding.status not in NEXT_STATUS:
            raise ValueError(f"Cannot advance from status {onboarding.status}")

        current_month = STATUS_TO_MONTH[onboarding.status]

        held_meeting = (
            await self.db.execute(
                select(Meeting).where(
                    Meeting.onboarding_id == onboarding_id,
                    Meeting.onboarding_month == current_month,
                    Meeting.status == MeetingStatus.HELD,
                )
            )
        ).scalars().first()

        if held_meeting is None:
            raise ValueError(
                f"Cannot advance: no held meeting found for month {current_month}"
            )

        onboarding.status = NEXT_STATUS[onboarding.status]
        await self.db.flush()
        return onboarding

    async def finalize_decision(
        self,
        onboarding_id: int,
        employee_decision: str,
        manager_decision: str,
    ) -> Onboarding:
        onboarding = await self._get(onboarding_id)

        if onboarding.status != OnboardingStatus.MONTH_3:
            raise ValueError("Final decision only allowed at MONTH_3")

        if employee_decision == "CONTINUE" and manager_decision == "CONTINUE":
            onboarding.status = OnboardingStatus.COMPLETED
        else:
            onboarding.status = OnboardingStatus.EXITED

        await self.db.flush()
        return onboarding