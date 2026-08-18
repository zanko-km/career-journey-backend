from datetime import date
from sqlalchemy import Date, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class PhaseStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class OnboardingPhase(Base):
    __tablename__ = "onboarding_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    onboarding_id: Mapped[int] = mapped_column(ForeignKey("onboardings.id"))
    phase_number: Mapped[int]
    title: Mapped[str]
    start_date: Mapped[date]
    end_date: Mapped[date]
    status: Mapped[PhaseStatus] = mapped_column(
        SAEnum(PhaseStatus), default=PhaseStatus.PENDING, nullable=False
    )