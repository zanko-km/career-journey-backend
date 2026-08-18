from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    employees = relationship(
        "Employee",
        back_populates="position",
    )