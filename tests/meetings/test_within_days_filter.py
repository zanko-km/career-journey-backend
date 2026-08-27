"""
Tests for the `withinDays` query param added to:
  - GET /meetings
  - GET /employees/{employee_id}/onboarding/actions

This replaces tests/meetings/test_upcoming_month_scope_gap.py, which used
to document the *absence* of this filter. That gap is now closed:
callers can pass `?withinDays=30` to scope results to "the next month"
(or any other window), while omitting the param preserves the old,
fully-unfiltered behaviour (verified below for backward compatibility).
"""

from datetime import date, datetime, timedelta

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Employee
from app.models.user import EmployeeRoleType

# ---------------------------------------------------------------------------
# GET /meetings?withinDays=
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_meetings_within_days_filters_out_far_future_meeting(
    client,
    db_session,
):
    from app.models import Meeting, MeetingParticipant, MeetingStatus

    employee = Employee(
        username="within_days_meetings",
        full_name="Onboarding Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    hr_manager = Employee(
        username="hr_manager_within_days",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    near_meeting = Meeting(
        organizer_id=hr_manager.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=10),
        status=MeetingStatus.PROPOSED,
    )
    far_meeting = Meeting(
        organizer_id=hr_manager.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=180),
        status=MeetingStatus.PROPOSED,
    )
    db_session.add_all([near_meeting, far_meeting])
    await db_session.flush()

    db_session.add_all(
        [
            MeetingParticipant(meeting_id=near_meeting.id, employee_id=employee.id),
            MeetingParticipant(meeting_id=far_meeting.id, employee_id=employee.id),
        ]
    )
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="within_days_meetings",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/meetings", params={"withinDays": 30})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    returned_ids = {m["id"] for m in response.json()}

    assert near_meeting.id in returned_ids
    assert far_meeting.id not in returned_ids


@pytest.mark.asyncio
async def test_meetings_without_within_days_returns_everything(
    client,
    db_session,
):
    """Backward compatibility: omitting the param keeps the old behaviour."""

    from app.models import Meeting, MeetingParticipant, MeetingStatus

    employee = Employee(
        username="no_filter_meetings",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    hr_manager = Employee(
        username="hr_manager_no_filter",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    far_meeting = Meeting(
        organizer_id=hr_manager.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() + timedelta(days=180),
        status=MeetingStatus.PROPOSED,
    )
    db_session.add(far_meeting)
    await db_session.flush()

    db_session.add(
        MeetingParticipant(meeting_id=far_meeting.id, employee_id=employee.id)
    )
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="no_filter_meetings",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    returned_ids = {m["id"] for m in response.json()}
    assert far_meeting.id in returned_ids


@pytest.mark.asyncio
async def test_meetings_within_days_excludes_past_meeting(
    client,
    db_session,
):
    """A meeting that already happened should not count as 'upcoming'."""

    from app.models import Meeting, MeetingParticipant, MeetingStatus

    employee = Employee(
        username="past_meeting_filter",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    hr_manager = Employee(
        username="hr_manager_past_filter",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    past_meeting = Meeting(
        organizer_id=hr_manager.id,
        employee_id=employee.id,
        scheduled_at=datetime.now() - timedelta(days=5),
        status=MeetingStatus.HELD,
    )
    db_session.add(past_meeting)
    await db_session.flush()

    db_session.add(
        MeetingParticipant(meeting_id=past_meeting.id, employee_id=employee.id)
    )
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="past_meeting_filter",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/meetings", params={"withinDays": 30})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    returned_ids = {m["id"] for m in response.json()}
    assert past_meeting.id not in returned_ids


@pytest.mark.asyncio
async def test_meetings_within_days_rejects_non_positive_value(client):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=1,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get("/meetings", params={"withinDays": 0})

    app.dependency_overrides.clear()

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /employees/{employee_id}/onboarding/actions?withinDays=
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_actions_within_days_filters_out_far_future_task(
    client,
    db_session,
):
    from app.models import Onboarding
    from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
    from app.models.onboarding_task import OnboardingTask

    employee = Employee(
        username="within_days_actions",
        full_name="Onboarding Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=1,
        title="Month 1",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=PhaseStatus.IN_PROGRESS,
    )
    db_session.add(phase)
    await db_session.flush()

    near_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="Due in 5 days",
        due_date=date.today() + timedelta(days=5),
        status="PENDING",
    )
    far_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="Due in 5 months",
        due_date=date.today() + timedelta(days=150),
        status="PENDING",
    )
    no_due_date_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="No due date",
        due_date=None,
        status="PENDING",
    )
    db_session.add_all([near_task, far_task, no_due_date_task])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="within_days_actions",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/employees/{employee.id}/onboarding/actions",
        params={"withinDays": 30},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()}

    assert "Due in 5 days" in titles
    assert "Due in 5 months" not in titles
    # Tasks without a due date have nothing to compare against a date
    # window, so they're excluded when a window is explicitly requested.
    assert "No due date" not in titles


@pytest.mark.asyncio
async def test_onboarding_actions_without_within_days_returns_everything(
    client,
    db_session,
):
    """Backward compatibility: omitting the param keeps the old behaviour,
    including tasks that have no due date at all."""

    from app.models import Onboarding
    from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
    from app.models.onboarding_task import OnboardingTask

    employee = Employee(
        username="no_filter_actions",
        full_name="Onboarding Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=1,
        title="Month 1",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=PhaseStatus.IN_PROGRESS,
    )
    db_session.add(phase)
    await db_session.flush()

    far_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="Due in 5 months",
        due_date=date.today() + timedelta(days=150),
        status="PENDING",
    )
    no_due_date_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="No due date",
        due_date=None,
        status="PENDING",
    )
    db_session.add_all([far_task, no_due_date_task])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="no_filter_actions",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(f"/employees/{employee.id}/onboarding/actions")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()}

    assert "Due in 5 months" in titles
    assert "No due date" in titles


@pytest.mark.asyncio
async def test_onboarding_actions_within_days_excludes_overdue_task(
    client,
    db_session,
):
    from app.models import Onboarding
    from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
    from app.models.onboarding_task import OnboardingTask

    employee = Employee(
        username="overdue_task_filter",
        full_name="Onboarding Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    onboarding = Onboarding(
        employee_id=employee.id,
        start_date=date.today(),
        duration_months=3,
    )
    db_session.add(onboarding)
    await db_session.flush()

    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=1,
        title="Month 1",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=PhaseStatus.IN_PROGRESS,
    )
    db_session.add(phase)
    await db_session.flush()

    overdue_task = OnboardingTask(
        phase_id=phase.id,
        assigned_by=employee.id,
        assigned_to=employee.id,
        title="Overdue task",
        due_date=date.today() - timedelta(days=3),
        status="PENDING",
    )
    db_session.add(overdue_task)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="overdue_task_filter",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/employees/{employee.id}/onboarding/actions",
        params={"withinDays": 30},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()}

    # KNOWN TRADE-OFF: an overdue-but-unfinished task is filtered out along
    # with far-future ones, since the filter is a pure date window. Callers
    # who need "everything still outstanding" should omit withinDays and
    # filter by status client-side instead.
    assert "Overdue task" not in titles


@pytest.mark.asyncio
async def test_onboarding_actions_within_days_rejects_non_positive_value(
    client,
    db_session,
):
    employee = Employee(
        username="bad_within_days_actions",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="bad_within_days_actions",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(
        f"/employees/{employee.id}/onboarding/actions",
        params={"withinDays": -5},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422