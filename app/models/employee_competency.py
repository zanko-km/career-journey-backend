from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EmployeeCompetency(Base):
    __tablename__ = "employee_competencies"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "competency_id",
            name="uq_employee_competency",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id"),
        nullable=False,
    )


    employee = relationship(
        "Employee",
        back_populates="competencies",
    )

    competency = relationship(
        "Competency",
        back_populates="employees",
    )