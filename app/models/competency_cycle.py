from datetime import date, datetime
import enum
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Boolean,
    String,
    Table,
    Column,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


competency_cycle_competencies = Table(
    "competency_cycle_competencies",
    Base.metadata,
    Column(
        "cycle_id",
        ForeignKey("competency_cycles.id"),
        primary_key=True,
    ),
    Column(
        "competency_id",
        ForeignKey("competencies.id"),
        primary_key=True,
    ),
)


class CompetencyCycleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SELF_ASSESSMENT_PENDING = "SELF_ASSESSMENT_PENDING"
    MANAGER_ASSESSMENT_PENDING = "MANAGER_ASSESSMENT_PENDING"
    REVIEW_PENDING = "REVIEW_PENDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class CompetencyCyclePhase(str, enum.Enum):
    RATING = "RATING"
    DEVELOPMENT = "DEVELOPMENT"
    REVIEW = "REVIEW"


class CompetencyCycle(Base):
    __tablename__ = "competency_cycles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
    )

    status: Mapped[CompetencyCycleStatus] = mapped_column(
        SAEnum(CompetencyCycleStatus),
        default=CompetencyCycleStatus.ACTIVE,
        nullable=False,
    )

    phase: Mapped[CompetencyCyclePhase] = mapped_column(
        SAEnum(CompetencyCyclePhase),
        default=CompetencyCyclePhase.RATING,
        nullable=False,
    )

    meeting_notes: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    meeting_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    focus_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    review_started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    review_started_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"),
        nullable=True,
    )


    employee = relationship(
        "Employee",
        foreign_keys=[employee_id],
    )

    review_started_by = relationship(
        "Employee",
        foreign_keys=[review_started_by_id],
    )

    focus_competencies = relationship(
        "Competency",
        secondary=competency_cycle_competencies,
    )
    manager_assessments = relationship(
        "CompetencyManagerAssessment",
        cascade="all, delete-orphan",
    )
    development_items = relationship(
        "DevelopmentPlanItem",
        back_populates="cycle",
        cascade="all, delete-orphan",
    )