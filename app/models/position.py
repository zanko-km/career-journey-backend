from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    job_description: Mapped[str | None] = mapped_column(default=None)
    default_onboarding_duration_months: Mapped[int] = mapped_column(default=3)
    employees = relationship(
        "Employee",
        back_populates="position",
    )