from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    onboarding_id: Mapped[int] = mapped_column(
        ForeignKey("onboardings.id"),
        unique=True,
        nullable=False,
    )

    goals: Mapped[str]
    skills: Mapped[str]
    training: Mapped[str]
    mentoring: Mapped[str]
    next_steps: Mapped[str]

    onboarding = relationship(
        "Onboarding",
        back_populates="development_plan",
    )