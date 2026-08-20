from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompetencyManagerAssessment(Base):

    __tablename__ = "competency_manager_assessments"

    __table_args__ = (
        UniqueConstraint(
            "cycle_id",
            "competency_id",
            name="uq_cycle_competency_manager_assessment",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("competency_cycles.id"),
        nullable=False,
    )

    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id"),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cycle = relationship(
        "CompetencyCycle",
        back_populates="manager_assessments",
    )

    competency = relationship(
        "Competency",
    )