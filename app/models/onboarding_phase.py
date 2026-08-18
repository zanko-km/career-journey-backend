from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class OnboardingPhase(Base):
    __tablename__ = "onboarding_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    onboarding_id: Mapped[int] = mapped_column(ForeignKey("onboardings.id"))
    phase_no: Mapped[int]
    status: Mapped[str] = mapped_column(default="PENDING")