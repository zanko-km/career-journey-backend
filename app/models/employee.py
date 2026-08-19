from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.position import Position
import enum


@property
def job_title(self) -> str | None:
    if self.position is None:
        return None

    return self.position.title


@job_title.setter
def job_title(self, value: str | None):
    if value is None:
        self.position = None
    else:
        self.position = Position(title=value)

class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXITED = "EXITED"


class ExitType(str, enum.Enum):
    RESIGNATION = "RESIGNATION"
    TERMINATION = "TERMINATION"


class CareerStage(str, enum.Enum):
    PRE_ONBOARDING = "PRE_ONBOARDING"
    ONBOARDING = "ONBOARDING"
    POST_ONBOARDING = "POST_ONBOARDING"
    EXITED = "EXITED"
    INACTIVE = "INACTIVE"

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str]
    nickname: Mapped[str | None]

    join_date: Mapped[date]

    monthly_salary: Mapped[float | None]

    status: Mapped[EmployeeStatus] = mapped_column(
        SAEnum(EmployeeStatus),
        default=EmployeeStatus.ACTIVE,
        nullable=False,
    )

    exit_type: Mapped[ExitType | None] = mapped_column(
        SAEnum(ExitType)
    )

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id")
    )

    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id")
    )

    position_id: Mapped[int | None] = mapped_column(
        ForeignKey("positions.id")
    )

    team = relationship(
        "Team",
        foreign_keys=[team_id],
        back_populates="employees",
    )

    manager = relationship(
        "Employee",
        remote_side=[id],
        foreign_keys=[manager_id],
        back_populates="direct_reports",
    )

    direct_reports = relationship(
        "Employee",
        foreign_keys=[manager_id],
        back_populates="manager",
    )
    
    position = relationship(
        "Position",
        back_populates="employees",
    )

    career_stage: Mapped[CareerStage] = mapped_column(
        SAEnum(CareerStage),
        default=CareerStage.PRE_ONBOARDING,
        nullable=False,
    )

    onboarding = relationship(
        "Onboarding",
        back_populates="employee",
        foreign_keys="Onboarding.employee_id",
        uselist=False,
    )
    
    roles = relationship(
        "EmployeeRole",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    
    @property
    def job_title(self) -> str | None:
        if self.position is None:
            return None

        return self.position.title

    @job_title.setter
    def job_title(self, value: str | None):
        if value is None:
            self.position = None
        else:
            self.position = Position(title=value)