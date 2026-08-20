from datetime import datetime

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.employee import Employee
from app.core.database import Base


class OnboardingFeedback(Base):
    __tablename__ = "onboarding_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )

    phase_id: Mapped[int | None] = mapped_column(
        ForeignKey("onboarding_phases.id"),
        nullable=True
    )

    meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id"),
        nullable=True
    )

    feedback: Mapped[str]

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(),
        nullable=False,
    )

    created_by: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[created_by_id],
    )