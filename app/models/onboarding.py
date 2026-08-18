from datetime import date
from sqlalchemy import Date, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class OnboardingStatus(str, enum.Enum):
    MONTH_1 = "MONTH_1"
    MONTH_2 = "MONTH_2"
    MONTH_3 = "MONTH_3"
    COMPLETED = "COMPLETED"
    EXITED = "EXITED"


class Onboarding(Base):
    __tablename__ = "onboardings"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    buddy_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))

    start_date: Mapped[date]
    end_date: Mapped[date | None]
    duration_months: Mapped[int] = mapped_column(default=3)

    status: Mapped[OnboardingStatus] = mapped_column(
        SAEnum(OnboardingStatus),
        default=OnboardingStatus.MONTH_1,
        nullable=False,
    )