from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum


class MeetingStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    HELD = "HELD"
    CANCELLED = "CANCELLED"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)

    organizer_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    participant_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))

    onboarding_id: Mapped[int | None] = mapped_column(ForeignKey("onboardings.id"))
    onboarding_month: Mapped[int | None]

    scheduled_at: Mapped[datetime]
    status: Mapped[MeetingStatus] = mapped_column(
        SAEnum(MeetingStatus),
        default=MeetingStatus.SCHEDULED,
        nullable=False,
    )