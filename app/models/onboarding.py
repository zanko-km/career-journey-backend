from datetime import date
from sqlalchemy import Date, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class OnboardingStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    FINAL_DECISION_PENDING = "FINAL_DECISION_PENDING"
    COMPLETED = "COMPLETED"
    EXITED = "EXITED"
    CANCELLED = "CANCELLED"


class Decision(str, enum.Enum):
    CONTINUE = "CONTINUE"
    EXIT = "EXIT"


class FinalResult(str, enum.Enum):
    PENDING = "PENDING"
    CONTINUE = "CONTINUE"
    EXIT = "EXIT"


class InvestmentDecision(str, enum.Enum):
    NONE = "NONE"
    INVESTMENT = "INVESTMENT"
    NORMAL = "NORMAL"


class Onboarding(Base):
    __tablename__ = "onboardings"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True)
    buddy_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))

    start_date: Mapped[date]
    end_date: Mapped[date | None]
    duration_months: Mapped[int] = mapped_column(default=3)

    status: Mapped[OnboardingStatus] = mapped_column(
        SAEnum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED, nullable=False
    )
    current_phase_number: Mapped[int | None]
    employee = relationship(
        "Employee",
        back_populates="onboarding",
        foreign_keys=[employee_id],
    )

    buddy = relationship(
        "Employee",
        foreign_keys=[buddy_id],
    )
    employee_decision: Mapped[Decision | None] = mapped_column(SAEnum(Decision))
    manager_decision: Mapped[Decision | None] = mapped_column(SAEnum(Decision))
    final_result: Mapped[FinalResult] = mapped_column(
        SAEnum(FinalResult), default=FinalResult.PENDING, nullable=False
    )
    investment_decision: Mapped[InvestmentDecision] = mapped_column(
        SAEnum(InvestmentDecision), default=InvestmentDecision.NONE, nullable=False
    )