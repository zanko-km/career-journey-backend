from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.user import EmployeeRoleType
from app.core.database import Base


class DevelopmentPlanItem(Base):
    __tablename__ = "development_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("competency_cycles.id"),
        nullable=False,
    )

    competency_id: Mapped[int] = mapped_column(
        ForeignKey("competencies.id"),
        nullable=False,
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    author_role: Mapped[EmployeeRoleType] = mapped_column(
        Enum(EmployeeRoleType),
        nullable=False,
    )

    completed: Mapped[bool] = mapped_column(
        default=False
    )

    comment: Mapped[str | None]

    task: Mapped[str | None]

    cycle = relationship(
        "CompetencyCycle",
        back_populates="development_items",
    )

    competency = relationship(
        "Competency",
    )

    author = relationship(
        "Employee",
    )