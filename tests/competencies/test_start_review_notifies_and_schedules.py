from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models import (
    Competency,
    Employee,
    EmployeeCompetency,
    Meeting,
    MeetingParticipant,
    Notification,
    User,
)
from app.models.competency_cycle import CompetencyCycle, CompetencyCycleStatus
from app.models.user import EmployeeRoleType


async def _make_active_cycle(db_session, employee, competency_names):
    competencies = []
    for name in competency_names:
        competency = Competency(name=name)
        db_session.add(competency)
        await db_session.flush()
        db_session.add(
            EmployeeCompetency(
                employee_id=employee.id,
                competency_id=competency.id,
            )
        )
        competencies.append(competency)

    cycle = CompetencyCycle(
        employee_id=employee.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=CompetencyCycleStatus.ACTIVE,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)
    return cycle, competencies


@pytest.mark.asyncio
async def test_start_review_notifies_manager_in_addition_to_employee(
    client,
    db_session,
):
    manager = Employee(
        username="start_review_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    manager_user = User(
        auth_provider_id="auth-start-review-manager",
        employee_id=manager.id,
    )
    db_session.add(manager_user)
    await db_session.flush()

    hrbp = Employee(
        username="start_review_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="start_review_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    employee_user = User(
        auth_provider_id="auth-start-review-employee",
        employee_id=employee.id,
    )
    db_session.add(employee_user)
    await db_session.flush()

    cycle, competencies = await _make_active_cycle(
        db_session, employee, ["Ownership"]
    )

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="start_review_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP, EmployeeRoleType.HR_MANAGER],
    )

    meeting_time = datetime.now() + timedelta(days=3)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [c.id for c in competencies],
            "meetingScheduledAt": meeting_time.isoformat(),
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    employee_notifs = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == employee_user.id,
                Notification.type == "PERFORMANCE_REVIEW_DEADLINE_SET",
            )
        )
    ).scalars().all()
    manager_notifs = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == manager_user.id,
                Notification.type == "PERFORMANCE_REVIEW_DEADLINE_SET",
            )
        )
    ).scalars().all()

    assert len(employee_notifs) == 1
    assert len(manager_notifs) == 1
    assert manager_notifs[0].reference_type == "COMPETENCY_CYCLE"


@pytest.mark.asyncio
async def test_start_review_without_manager_does_not_error(
    client,
    db_session,
):
    """Regression guard: an employee with no manager must not break the
    endpoint just because there's no one to notify."""

    hrbp = Employee(
        username="start_review_no_manager_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="start_review_no_manager_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=None,
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, competencies = await _make_active_cycle(
        db_session, employee, ["Ownership"]
    )

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="start_review_no_manager_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP, EmployeeRoleType.HR_MANAGER],
    )

    meeting_time = datetime.now() + timedelta(days=3)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [c.id for c in competencies],
            "meetingScheduledAt": meeting_time.isoformat(),
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_start_review_with_meeting_scheduled_at_creates_meeting(
    client,
    db_session,
):
    manager = Employee(
        username="start_review_meeting_manager",
        full_name="Manager",
        join_date=date.today(),
    )
    db_session.add(manager)
    await db_session.flush()

    manager_user = User(
        auth_provider_id="auth-start-review-meeting-manager",
        employee_id=manager.id,
    )
    db_session.add(manager_user)
    await db_session.flush()

    hrbp = Employee(
        username="start_review_meeting_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="start_review_meeting_employee",
        full_name="Employee",
        join_date=date.today(),
        manager_id=manager.id,
    )
    db_session.add(employee)
    await db_session.flush()

    employee_user = User(
        auth_provider_id="auth-start-review-meeting-employee",
        employee_id=employee.id,
    )
    db_session.add(employee_user)
    await db_session.flush()

    cycle, competencies = await _make_active_cycle(
        db_session, employee, ["Ownership"]
    )

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="start_review_meeting_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP, EmployeeRoleType.HR_MANAGER],
    )

    meeting_time = datetime.now() + timedelta(days=3)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [c.id for c in competencies],
            "meetingScheduledAt": meeting_time.isoformat(),
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    meeting_result = await db_session.execute(
        select(Meeting).where(Meeting.employee_id == employee.id)
    )
    meeting = meeting_result.scalar_one()
    assert meeting.organizer_id == hrbp.id

    participants_result = await db_session.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting.id
        )
    )
    participant_ids = {
        p.employee_id for p in participants_result.scalars().all()
    }
    assert participant_ids == {hrbp.id, employee.id, manager.id}

    manager_notifs = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == manager_user.id,
                Notification.type == "MEETING_SCHEDULED",
            )
        )
    ).scalars().all()
    employee_notifs = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == employee_user.id,
                Notification.type == "MEETING_SCHEDULED",
            )
        )
    ).scalars().all()

    assert len(manager_notifs) == 1
    assert len(employee_notifs) == 1


@pytest.mark.asyncio
async def test_start_review_without_meeting_scheduled_at_returns_422(
    client,
    db_session,
):
    """meetingScheduledAt is required: starting a review is meant to put
    the HRBP into a meeting with the employee and their manager, so
    omitting it must be rejected rather than silently skipping the
    meeting."""

    hrbp = Employee(
        username="start_review_no_meeting_hrbp",
        full_name="HRBP",
        join_date=date.today(),
    )
    db_session.add(hrbp)
    await db_session.flush()

    employee = Employee(
        username="start_review_no_meeting_employee",
        full_name="Employee",
        join_date=date.today(),
    )
    db_session.add(employee)
    await db_session.flush()

    cycle, competencies = await _make_active_cycle(
        db_session, employee, ["Ownership"]
    )

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hrbp.id,
        username="start_review_no_meeting_hrbp",
        full_name="HRBP",
        roles=[EmployeeRoleType.HRBP, EmployeeRoleType.HR_MANAGER],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={"competencyIds": [c.id for c in competencies]},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422

    meeting_result = await db_session.execute(
        select(Meeting).where(Meeting.employee_id == employee.id)
    )
    assert meeting_result.scalar_one_or_none() is None