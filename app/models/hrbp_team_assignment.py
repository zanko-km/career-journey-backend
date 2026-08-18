from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HrbpTeamAssignment(Base):

    __tablename__ = "hrbp_team_assignments"

    __table_args__ = (
        UniqueConstraint(
            "hrbp_id",
            "team_id",
            name="uq_hrbp_team"
        ),
    )


    id: Mapped[int] = mapped_column(primary_key=True)

    hrbp_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id")
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id")
    )


    team = relationship(
        "Team",
        back_populates="hrbp_assignments"
    )


    hrbp = relationship(
        "Employee",
        foreign_keys=[hrbp_id]
    )