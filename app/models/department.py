from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str]

    description: Mapped[str | None]

    teams = relationship(
        "Team",
        back_populates="department"
    )