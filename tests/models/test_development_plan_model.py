import pytest
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.models import Employee, Onboarding, DevelopmentPlan


@pytest.mark.asyncio
async def test_onboarding_can_have_development_plan(db_session):
    employee = Employee(
        username="dev_plan_employee",
        full_name="Development Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        current_phase_number=1,
    )

    db_session.add(onboarding)
    await db_session.flush()

    plan = DevelopmentPlan(
        onboarding_id=onboarding.id,
        goals="Improve backend skills",
        skills="Python FastAPI",
        training="System Design",
        mentoring="Senior backend mentoring",
        next_steps="Build production features",
    )

    db_session.add(plan)
    await db_session.flush()

    assert plan.id is not None
    assert plan.onboarding_id == onboarding.id


@pytest.mark.asyncio
async def test_development_plan_relationship_with_onboarding(db_session):
    employee = Employee(
        username="dev_plan_relation",
        full_name="Relation Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        current_phase_number=1,
    )

    plan = DevelopmentPlan(
        goals="Goal",
        skills="Skill",
        training="Training",
        mentoring="Mentoring",
        next_steps="Next step",
    )

    onboarding.development_plan = plan

    db_session.add(onboarding)
    await db_session.flush()

    assert onboarding.development_plan == plan
    assert plan.onboarding_id == onboarding.id


@pytest.mark.asyncio
async def test_onboarding_cannot_have_multiple_development_plans(
    db_session,
):
    employee = Employee(
        username="dev_plan_unique",
        full_name="Unique Employee",
        join_date=date.today(),
    )

    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
    )

    db_session.add(onboarding)
    await db_session.flush()

    plan1 = DevelopmentPlan(
        onboarding_id=onboarding.id,
        goals="Goal 1",
        skills="Skill",
        training="Training",
        mentoring="Mentoring",
        next_steps="Next",
    )

    plan2 = DevelopmentPlan(
        onboarding_id=onboarding.id,
        goals="Goal 2",
        skills="Skill",
        training="Training",
        mentoring="Mentoring",
        next_steps="Next",
    )

    db_session.add(plan1)
    await db_session.flush()

    db_session.add(plan2)

    with pytest.raises(IntegrityError):
        await db_session.flush()