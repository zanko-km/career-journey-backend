from datetime import date, datetime

import pytest

from app.models import (
    Decision,
    Employee,
    ExitType,
    Onboarding,
    OnboardingStatus,
)
from app.services.meeting import MeetingService
from app.services.onboarding import OnboardingService

ALL_STATUSES = list(OnboardingStatus)
NON_IN_PROGRESS_STATUSES = [s for s in ALL_STATUSES if s != OnboardingStatus.IN_PROGRESS]
NON_FINAL_DECISION_STATUSES = [s for s in ALL_STATUSES if s != OnboardingStatus.FINAL_DECISION_PENDING]


async def _make_employee(db_session, tag: str) -> Employee:
    emp = Employee(username=f"emp_{tag}", full_name=f"Employee {tag}", join_date=date.today())
    db_session.add(emp)
    await db_session.flush()
    return emp


async def _make_onboarding(db_session, status: OnboardingStatus, phase: int | None = 1) -> Onboarding:
    emp = await _make_employee(db_session, status.value)
    onboarding = Onboarding(
        employee_id=emp.id,
        start_date=date.today(),
        status=status,
        current_phase_number=phase,
    )
    db_session.add(onboarding)
    await db_session.flush()
    return onboarding


@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_IN_PROGRESS_STATUSES)
async def test_advance_rejected_from_every_non_in_progress_status(db_session, status):
    onboarding = await _make_onboarding(db_session, status)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="Cannot advance from status"):
        await service.advance_to_next_phase(onboarding.id)

    await db_session.refresh(onboarding)
    assert onboarding.status == status


@pytest.mark.asyncio
async def test_advance_rejected_when_in_progress_but_no_phase_number(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.IN_PROGRESS, phase=None)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="no active phase"):
        await service.advance_to_next_phase(onboarding.id)


@pytest.mark.asyncio
async def test_advance_rejected_without_held_meeting_for_current_phase(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.IN_PROGRESS)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="no held meeting"):
        await service.advance_to_next_phase(onboarding.id)


@pytest.mark.asyncio
async def test_advance_moves_to_final_decision_pending_after_last_phase(db_session):
    emp = await _make_employee(db_session, "final")
    hrbp = await _make_employee(db_session, "hrbp_final")
    onboarding_service = OnboardingService(db_session)
    meeting_service = MeetingService(db_session)

    onboarding = await onboarding_service.start_onboarding(emp.id, date.today())
    assert onboarding.duration_months == 3

    for phase in (1, 2, 3):
        meeting = await meeting_service.schedule(
            organizer_id=hrbp.id,
            participant_ids=[emp.id],
            scheduled_at=datetime.now(),
            onboarding_id=onboarding.id,
            onboarding_month=phase,
        )
        await meeting_service.confirm(meeting.id)
        await meeting_service.mark_held(meeting.id, emp.id)
        onboarding = await onboarding_service.advance_to_next_phase(onboarding.id)

    assert onboarding.status == OnboardingStatus.FINAL_DECISION_PENDING
    assert onboarding.current_phase_number == 3



@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_FINAL_DECISION_STATUSES)
async def test_submit_employee_decision_rejected_from_every_other_status(db_session, status):
    onboarding = await _make_onboarding(db_session, status)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="FINAL_DECISION_PENDING"):
        await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)

    await db_session.refresh(onboarding)
    assert onboarding.status == status


@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_FINAL_DECISION_STATUSES)
async def test_submit_manager_decision_rejected_from_every_other_status(db_session, status):
    onboarding = await _make_onboarding(db_session, status)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="FINAL_DECISION_PENDING"):
        await service.submit_manager_decision(onboarding.id, Decision.CONTINUE)

    await db_session.refresh(onboarding)
    assert onboarding.status == status


@pytest.mark.asyncio
async def test_employee_decision_cannot_be_submitted_twice(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)

    with pytest.raises(ValueError, match="already submitted"):
        await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)


@pytest.mark.asyncio
async def test_manager_decision_is_not_guarded_against_resubmission(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    await service.submit_manager_decision(onboarding.id, Decision.CONTINUE)
    # second call does NOT raise today
    result = await service.submit_manager_decision(onboarding.id, Decision.EXIT, exit_type=ExitType.TERMINATION)

    assert result.manager_decision == Decision.EXIT


@pytest.mark.asyncio
async def test_manager_decision_exit_requires_exit_type(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    with pytest.raises(ValueError, match="exit_type is required"):
        await service.submit_manager_decision(onboarding.id, Decision.EXIT)


@pytest.mark.asyncio
async def test_employee_decision_exit_defaults_exit_type_to_resignation(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    updated = await service.submit_employee_decision(onboarding.id, Decision.EXIT)

    assert updated.status == OnboardingStatus.EXITED
    assert updated.final_result.value == "EXIT"

    employee = await db_session.get(Employee, onboarding.employee_id)
    assert employee.status.value == "EXITED"
    assert employee.exit_type == ExitType.RESIGNATION


@pytest.mark.asyncio
async def test_manager_decision_exit_type_is_recorded_on_employee(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    updated = await service.submit_manager_decision(
        onboarding.id, Decision.EXIT, exit_type=ExitType.TERMINATION
    )

    assert updated.status == OnboardingStatus.EXITED

    employee = await db_session.get(Employee, onboarding.employee_id)
    assert employee.status.value == "EXITED"
    assert employee.exit_type == ExitType.TERMINATION


@pytest.mark.asyncio
async def test_both_continue_completes_onboarding(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    result = await service.submit_manager_decision(onboarding.id, Decision.CONTINUE)

    assert result.status == OnboardingStatus.COMPLETED
    assert result.final_result.value == "CONTINUE"


@pytest.mark.asyncio
async def test_manager_exit_after_employee_continue_exits_onboarding(db_session):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    await service.submit_employee_decision(onboarding.id, Decision.CONTINUE)
    result = await service.submit_manager_decision(
        onboarding.id, Decision.EXIT, exit_type=ExitType.RESIGNATION
    )

    assert result.status == OnboardingStatus.EXITED


@pytest.mark.asyncio
@pytest.mark.parametrize("employee_decision", [Decision.EXIT])
async def test_employee_exit_alone_finalizes_immediately_without_waiting_for_manager(
    db_session, employee_decision
):
    onboarding = await _make_onboarding(db_session, OnboardingStatus.FINAL_DECISION_PENDING)
    service = OnboardingService(db_session)

    result = await service.submit_employee_decision(onboarding.id, employee_decision)

    assert result.status == OnboardingStatus.EXITED
    assert result.final_result.value == "EXIT"

    with pytest.raises(ValueError, match="FINAL_DECISION_PENDING"):
        await service.submit_manager_decision(onboarding.id, Decision.CONTINUE)
