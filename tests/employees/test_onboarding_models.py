import pytest
from datetime import date
from app.models import Employee, Onboarding, OnboardingStatus


@pytest.mark.asyncio
async def test_onboarding_can_be_created_for_employee(db_session):
    emp = Employee(username="new_hire", full_name="New Hire", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()

    onboarding = Onboarding(employee_id=emp.id, start_date=date.today())
    db_session.add(onboarding)
    await db_session.flush()

    assert onboarding.status == OnboardingStatus.NOT_STARTED
    assert onboarding.duration_months == 3