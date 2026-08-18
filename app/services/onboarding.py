from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Onboarding, OnboardingStatus, Decision, FinalResult
from app.models import Meeting, MeetingStatus


class OnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_onboarding(self, employee_id: int, start_date: date) -> Onboarding:
        onboarding = Onboarding(
            employee_id=employee_id,
            start_date=start_date,
            status=OnboardingStatus.IN_PROGRESS,
            current_phase_number=1,
        )
        self.db.add(onboarding)
        await self.db.flush()
        return onboarding

    async def _get(self, onboarding_id: int) -> Onboarding:
        onboarding = await self.db.get(Onboarding, onboarding_id)
        if onboarding is None:
            raise ValueError("Onboarding not found")
        return onboarding

    async def advance_to_next_phase(self, onboarding_id: int) -> Onboarding:
        onboarding = await self._get(onboarding_id)

        if onboarding.status != OnboardingStatus.IN_PROGRESS:
            raise ValueError(f"Cannot advance from status {onboarding.status}")

        current_phase = onboarding.current_phase_number
        if current_phase is None:
            raise ValueError("Onboarding has no active phase to advance from")

        held_meeting = (
            await self.db.execute(
                select(Meeting).where(
                    Meeting.onboarding_id == onboarding_id,
                    Meeting.onboarding_month == current_phase,
                    Meeting.status == MeetingStatus.HELD,
                )
            )
        ).scalars().first()

        if held_meeting is None:
            raise ValueError(
                f"Cannot advance: no held meeting found for phase {current_phase}"
            )

        next_phase = current_phase + 1
        if next_phase > onboarding.duration_months:
            onboarding.status = OnboardingStatus.FINAL_DECISION_PENDING
        else:
            onboarding.current_phase_number = next_phase

        await self.db.flush()
        return onboarding

    async def submit_employee_decision(self, onboarding_id: int, decision: Decision) -> Onboarding:
        onboarding = await self._get(onboarding_id)
        if onboarding.status != OnboardingStatus.FINAL_DECISION_PENDING:
            raise ValueError("Employee decision only allowed while FINAL_DECISION_PENDING")
        onboarding.employee_decision = decision
        await self._finalize_if_both_decided(onboarding)
        return onboarding

    async def submit_manager_decision(self, onboarding_id: int, decision: Decision) -> Onboarding:
        onboarding = await self._get(onboarding_id)
        if onboarding.status != OnboardingStatus.FINAL_DECISION_PENDING:
            raise ValueError("Manager decision only allowed while FINAL_DECISION_PENDING")
        onboarding.manager_decision = decision
        await self._finalize_if_both_decided(onboarding)
        return onboarding

    async def _finalize_if_both_decided(self, onboarding: Onboarding) -> None:
        if onboarding.employee_decision is None or onboarding.manager_decision is None:
            await self.db.flush()
            return

        if (
            onboarding.employee_decision == Decision.CONTINUE
            and onboarding.manager_decision == Decision.CONTINUE
        ):
            onboarding.status = OnboardingStatus.COMPLETED
            onboarding.final_result = FinalResult.CONTINUE
        else:
            onboarding.status = OnboardingStatus.EXITED
            onboarding.final_result = FinalResult.EXIT

        await self.db.flush()