from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


from sqlalchemy.orm import relationship


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]

    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id")
    )

    team_manager_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )


    department = relationship(
        "Department",
        back_populates="teams"
    )


    team_manager = relationship(
        "Employee",
        foreign_keys=[team_manager_id]
    )


    employees = relationship(
        "Employee",
        back_populates="team",
        foreign_keys="Employee.team_id"
    )

    hrbp_assignments = relationship(
        "HrbpTeamAssignment",
        back_populates="team"
    )

    hrbps = relationship(
        "Employee",
        secondary="hrbp_team_assignments",
        primaryjoin="Team.id == HrbpTeamAssignment.team_id",
        secondaryjoin="Employee.id == HrbpTeamAssignment.hrbp_id",
        viewonly=True
    )