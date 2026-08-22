import pytest
from app.models.user import User
from app.models.employee import Employee
from datetime import date

@pytest.mark.asyncio
async def test_user_can_be_created(db_session):
    employee = Employee(username="ali", full_name="Ali", join_date=date.today())
    db_session.add(employee)
    await db_session.flush()

    user = User(auth_provider_id="supabase-user-123", employee_id=employee.id)
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None