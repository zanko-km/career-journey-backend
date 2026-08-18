import pytest
from datetime import date

from app.models.employee import Employee, EmployeeStatus


@pytest.mark.asyncio
async def test_employee_can_be_created(db_session):
    employee = Employee(
        username="test@gmail.com",
        full_name="Test User",
        nickname=None,
        join_date=date(2026, 8, 18),
        monthly_salary=5000,
        status=EmployeeStatus.ACTIVE,
    )

    db_session.add(employee)
    await db_session.commit()

    assert employee.id is not None
    assert employee.username == "test@gmail.com"
    assert employee.full_name == "Test User"
    assert employee.status == EmployeeStatus.ACTIVE