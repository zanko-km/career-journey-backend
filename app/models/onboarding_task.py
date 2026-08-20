from datetime import date
from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    phase_id: Mapped[int] = mapped_column(
        ForeignKey("onboarding_phases.id")
    )

    assigned_by: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )

    assigned_to: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )
    
    title: Mapped[str]

    description: Mapped[str | None]

    due_date: Mapped[date | None]

    status: Mapped[str] = mapped_column(
        default="PENDING"
    )
    assigned_by_employee = relationship(
        "Employee",
        foreign_keys=[assigned_by]
    )