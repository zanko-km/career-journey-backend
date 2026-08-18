from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

import enum


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str]
    full_name: Mapped[str]
    nickname: Mapped[str | None]

    join_date: Mapped[date]

    monthly_salary: Mapped[float | None]

    status: Mapped[EmployeeStatus] = mapped_column(
        SAEnum(EmployeeStatus),
        default=EmployeeStatus.ACTIVE,
        nullable=False,
    )
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))