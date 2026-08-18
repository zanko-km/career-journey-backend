import pytest
from datetime import date, datetime
from app.models import Employee, OnboardingStatus, Decision
from app.services.onboarding import OnboardingService
from app.services.meeting import MeetingService


@pytest.mark.asyncio
async def test_onboarding_starts_in_progress_at_phase_1(db_session):
    emp = Employee(username="new_hire", full_name="New Hire", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()

    service = OnboardingService(db_session)
    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    assert onboarding.status == OnboardingStatus.IN_PROGRESS
    assert onboarding.current_phase_number == 1


@pytest.mark.asyncio
async def test_advance_from_phase_1_to_phase_2(db_session):
    emp = Employee(username="new_hire2", full_name="New Hire 2", join_date=date.today())
    hrbp = Employee(username="hrbp_m1", full_name="HRBP M1", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())

    meeting = await meeting_service.schedule(
        hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=1
    )
    await meeting_service.confirm(meeting.id)
    await meeting_service.mark_held(meeting.id)

    updated = await onboarding_service.advance_to_next_phase(onboarding.id)
    assert updated.current_phase_number == 2
    assert updated.status == OnboardingStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_cannot_advance_without_a_held_meeting_for_current_phase(db_session):
    emp = Employee(username="new_hire7", full_name="New Hire 7", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()

    service = OnboardingService(db_session)
    onboarding = await service.start_onboarding(employee_id=emp.id, start_date=date.today())

    with pytest.raises(ValueError):
        await service.advance_to_next_phase(onboarding.id)


async def _bring_onboarding_to_final_decision(onboarding_service, meeting_service, emp, hrbp, onboarding):
    for phase in (1, 2, 3):
        meeting = await meeting_service.schedule(
            hrbp.id, emp.id, datetime.now(), onboarding_id=onboarding.id, onboarding_month=phase
        )
        await meeting_service.confirm(meeting.id)
        await meeting_service.mark_held(meeting.id)
        onboarding = await onboarding_service.advance_to_next_phase(onboarding.id)
    return onboarding


@pytest.mark.asyncio
async def test_completing_final_phase_moves_to_final_decision_pending(db_session):
    emp = Employee(username="new_hire8", full_name="New Hire 8", join_date=date.today())
    hrbp = Employee(username="hrbp8", full_name="HRBP Eight", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())
    onboarding = await _bring_onboarding_to_final_decision(
        onboarding_service, meeting_service, emp, hrbp, onboarding
    )

    assert onboarding.status == OnboardingStatus.FINAL_DECISION_PENDING


@pytest.mark.asyncio
async def test_final_decision_continue_when_both_agree(db_session):
    emp = Employee(username="new_hire3", full_name="New Hire 3", join_date=date.today())
    hrbp = Employee(username="hrbp_m3a", full_name="HRBP M3A", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)
    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())
    onboarding = await _bring_onboarding_to_final_decision(
        onboarding_service, meeting_service, emp, hrbp, onboarding
    )

    await onboarding_service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    result = await onboarding_service.submit_manager_decision(onboarding.id, Decision.CONTINUE)

    assert result.status == OnboardingStatus.COMPLETED


@pytest.mark.asyncio
async def test_final_decision_exit_when_either_disagrees(db_session):
    emp = Employee(username="new_hire4", full_name="New Hire 4", join_date=date.today())
    hrbp = Employee(username="hrbp_m3b", full_name="HRBP M3B", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)
    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())
    onboarding = await _bring_onboarding_to_final_decision(
        onboarding_service, meeting_service, emp, hrbp, onboarding
    )

    await onboarding_service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    result = await onboarding_service.submit_manager_decision(onboarding.id, Decision.EXIT)

    assert result.status == OnboardingStatus.EXITED


@pytest.mark.asyncio
async def test_decision_not_finalized_until_both_sides_submit(db_session):
    emp = Employee(username="new_hire9", full_name="New Hire 9", join_date=date.today())
    hrbp = Employee(username="hrbp9", full_name="HRBP Nine", join_date=date.today())
    db_session.add_all([emp, hrbp])
    await db_session.flush()

    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)
    onboarding = await onboarding_service.start_onboarding(employee_id=emp.id, start_date=date.today())
    onboarding = await _bring_onboarding_to_final_decision(
        onboarding_service, meeting_service, emp, hrbp, onboarding
    )

    only_employee = await onboarding_service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    assert only_employee.status == OnboardingStatus.FINAL_DECISION_PENDING