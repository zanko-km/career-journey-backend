from sqlalchemy import ForeignKey, Boolean, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
import enum


class MeetingResponseStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "employee_id",
            name="uq_meeting_participant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id"),
        nullable=False,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    response_status: Mapped[MeetingResponseStatus] = mapped_column(
        SAEnum(MeetingResponseStatus),
        default=MeetingResponseStatus.PENDING,
        nullable=False,
    )

    held_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    meeting = relationship(
        "Meeting",
        back_populates="participants",
    )

    employee = relationship(
        "Employee"
    )