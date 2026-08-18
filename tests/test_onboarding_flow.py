import pytest
from datetime import date
from app.models import Employee, Onboarding, OnboardingStatus
from app.services.onboarding import OnboardingService


@pytest.mark.asyncio
async def test_onboarding_starts_at_month_1(db_session):
    emp = Employee(username="new_hire", full_name="New Hire", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()

    service = OnboardingService(db_session)
    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    assert onboarding.status == OnboardingStatus.MONTH_1


@pytest.mark.asyncio
async def test_advance_from_month_1_to_month_2(db_session):
    from app.services.meeting import MeetingService
    from datetime import datetime

    emp = Employee(username="new_hire2", full_name="New Hire 2", join_date=date.today())
    hrbp = Employee(username="hrbp_m1", full_name="HRBP M1", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    meeting = await meeting_service.schedule(
        hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=1
    )
    await meeting_service.confirm(meeting.id)
    await meeting_service.mark_held(meeting.id)

    updated = await service.advance_to_next_month(onboarding.id)
    assert updated.status == OnboardingStatus.MONTH_2


@pytest.mark.asyncio
async def test_final_decision_continue_when_both_agree(db_session):
    from app.services.meeting import MeetingService
    from datetime import datetime

    emp = Employee(username="new_hire3", full_name="New Hire 3", join_date=date.today())
    hrbp = Employee(username="hrbp_m3a", full_name="HRBP M3A", join_date=date.today())
    manager = Employee(username="mgr_m3a", full_name="Manager M3A", join_date=date.today())
    db_session.add_all([emp, hrbp, manager])
    await db_session.flush()

    service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    m1 = await meeting_service.schedule(
        hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=1
    )
    await meeting_service.confirm(m1.id)
    await meeting_service.mark_held(m1.id)
    await service.advance_to_next_month(onboarding.id)

    m2 = await meeting_service.schedule(
        manager.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=2
    )
    await meeting_service.confirm(m2.id)
    await meeting_service.mark_held(m2.id)
    await service.advance_to_next_month(onboarding.id)

    result = await service.finalize_decision(
        onboarding.id,
        employee_decision="CONTINUE",
        manager_decision="CONTINUE",
    )

    assert result.status == OnboardingStatus.COMPLETED


@pytest.mark.asyncio
async def test_final_decision_exit_when_either_disagrees(db_session):
    from app.services.meeting import MeetingService
    from datetime import datetime

    emp = Employee(username="new_hire4", full_name="New Hire 4", join_date=date.today())
    hrbp = Employee(username="hrbp_m3b", full_name="HRBP M3B", join_date=date.today())
    manager = Employee(username="mgr_m3b", full_name="Manager M3B", join_date=date.today())
    db_session.add_all([emp, hrbp, manager])
    await db_session.flush()

    service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    m1 = await meeting_service.schedule(
        hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=1
    )
    await meeting_service.confirm(m1.id)
    await meeting_service.mark_held(m1.id)
    await service.advance_to_next_month(onboarding.id)

    m2 = await meeting_service.schedule(
        manager.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=2
    )
    await meeting_service.confirm(m2.id)
    await meeting_service.mark_held(m2.id)
    await service.advance_to_next_month(onboarding.id)

    result = await service.finalize_decision(
        onboarding.id,
        employee_decision="CONTINUE",
        manager_decision="EXIT",
    )

    assert result.status == OnboardingStatus.EXITED
    
    
@pytest.mark.asyncio
async def test_cannot_advance_using_stale_meeting_from_previous_month(db_session):
    from app.services.meeting import MeetingService
    from datetime import datetime

    emp = Employee(username="new_hire7", full_name="New Hire 7", join_date=date.today())
    hrbp = Employee(username="hrbp7", full_name="HRBP Seven", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    m1 = await meeting_service.schedule(
        hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=1
    )
    await meeting_service.confirm(m1.id)
    await meeting_service.mark_held(m1.id)
    await service.advance_to_next_month(onboarding.id)

    with pytest.raises(ValueError):
        await service.advance_to_next_month(onboarding.id)


@pytest.mark.asyncio
async def test_can_advance_month_after_meeting_held(db_session):
    from app.services.meeting import MeetingService
    from datetime import datetime

    emp = Employee(username="new_hire6", full_name="New Hire 6", join_date=date.today())
    hrbp = Employee(username="hrbp6", full_name="HRBP Six", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())

    meeting = await meeting_service.schedule(
        organizer_id=hrbp.id,
        participant_id=emp.id,
        scheduled_at=datetime.now(),
        onboarding_id=onboarding.id,
        onboarding_month=1,
    )
    await meeting_service.confirm(meeting.id)
    await meeting_service.mark_held(meeting.id)

    updated = await onboarding_service.advance_to_next_month(onboarding.id)
    assert updated.status.value == "MONTH_2"