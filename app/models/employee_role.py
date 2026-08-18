from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class EmployeeRole(Base):
    __tablename__ = "employee_role"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int]= mapped_column(ForeignKey("employees.id"))
    role: Mapped[str]