"""
GAP TEST — documents missing behavior, does not exercise a real feature.

Product requirement: "an Employee in Onboarding must be able to see the
meetings and plans for the *next month* only."

Current implementation has no server-side date-range filtering anywhere:
  - `GET /meetings` returns every meeting the employee organizes/participates
    in, regardless of `scheduled_at`.
  - `GET /employees/{id}/onboarding/actions` returns every task in every
    phase, regardless of `due_date`.
  - Neither route accepts a `from`/`to`/`month` query parameter
    (grep for `Query(` in app/api/routes/ returns nothing).

These tests assert the *current* behavior (a meeting 6 months out is
returned identically to a meeting tomorrow) so that:
  1. It's obvious in CI that this is a known gap, not silently missing.
  2. If a `?within_days=` (or similar) filter is added later, these tests
     will fail and must be updated — which is the intended signal.

If/when the backend adds real scoping, delete this file and replace it
with a positive test asserting the filtered result.
"""

from datetime import date, datetime, timedelta

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import Employee, HrbpTeamAssignment
from app.models.user import EmployeeRoleType


@pytest.mark.asyncio
async def test_meetings_endpoint_has_no_date_range_filter(
    client,
    db_session,
):
    employee = Employee(
        username="onboarding_scope_gap",
        full_name="Onboarding Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    hr_manager = Employee(
        username="hr_manager_scope_gap",
        full_name="HR Manager",
        join_date=date.today(),
    )
    db_session.add(hr_manager)
    await db_session.flush()

    from app.models.employee_role import EmployeeRole

    db_session.add(EmployeeRole(employee_id=hr_manager.id, role="HR_MANAGER"))
    await db_session.flush()

    # One meeting within the "next month", one meeting 6 months away.
    from app.models import Meeting, MeetingParticipant, MeetingStatus

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
        username="onboarding_scope_gap",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    # No query params exist to scope this to "next month" — the API has
    # no such parameter today.
    response = await client.get("/meetings")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    returned_ids = {m["id"] for m in response.json()}

    # KNOWN GAP: both the near and the far-future meeting come back
    # together, undistinguished. A real "next month" view currently has
    # to be built client-side by filtering `scheduledAt` in the response.
    assert near_meeting.id in returned_ids
    assert far_meeting.id in returned_ids


@pytest.mark.asyncio
async def test_onboarding_actions_endpoint_has_no_date_range_filter(
    client,
    db_session,
):
    from app.models import Onboarding
    from app.models.onboarding_phase import OnboardingPhase, PhaseStatus
    from app.models.onboarding_task import OnboardingTask

    employee = Employee(
        username="onboarding_actions_scope_gap",
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
    db_session.add_all([near_task, far_task])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee.id,
        username="onboarding_actions_scope_gap",
        full_name="Onboarding Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )

    response = await client.get(f"/employees/{employee.id}/onboarding/actions")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    titles = {t["title"] for t in response.json()}

    # KNOWN GAP: both near and far-future tasks are returned together;
    # there is no due_date-based scoping to "next month" on this endpoint.
    assert "Due in 5 days" in titles
    assert "Due in 5 months" in titles