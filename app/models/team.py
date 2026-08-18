from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]