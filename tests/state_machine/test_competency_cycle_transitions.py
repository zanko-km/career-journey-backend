from datetime import date, datetime

import pytest

from app.core.current_user import AuthenticatedUser, get_current_user
from app.main import app
from app.models.competency import Competency
from app.models.competency_cycle import (
    CompetencyCycle,
    CompetencyCyclePhase,
    CompetencyCycleStatus,
)
from app.models.competency_manager_assessment import CompetencyManagerAssessment
from app.models.competency_self_assessment import CompetencySelfAssessment
from app.models.employee import Employee
from app.models.employee_competency import EmployeeCompetency
from app.models.user import EmployeeRoleType

ALL_STATUSES = list(CompetencyCycleStatus)
NON_ACTIVE_STATUSES = [s for s in ALL_STATUSES if s != CompetencyCycleStatus.ACTIVE]
NON_SELF_ASSESSMENT_PENDING_STATUSES = [
    s for s in ALL_STATUSES if s != CompetencyCycleStatus.SELF_ASSESSMENT_PENDING
]


async def _make_employee(db_session, tag: str) -> Employee:
    emp = Employee(username=f"emp_{tag}", full_name=f"Employee {tag}", join_date=date.today())
    db_session.add(emp)
    await db_session.commit()
    return emp


async def _make_cycle(db_session, employee_id: int, status: CompetencyCycleStatus, **kwargs) -> CompetencyCycle:
    cycle = CompetencyCycle(
        employee_id=employee_id,
        start_date=date.today(),
        end_date=date.today(),
        status=status,
        phase=CompetencyCyclePhase.RATING,
        **kwargs,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)
    return cycle


async def _as_hr_manager(db_session):
    hr_manager = await _make_employee(db_session, "hr_manager")
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=hr_manager.id,
        username="hr_manager",
        full_name="HR Manager",
        roles=[EmployeeRoleType.HR_MANAGER],
    )
    return hr_manager


def _as_employee(employee_id: int):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=1,
        employee_id=employee_id,
        username="employee",
        full_name="Employee",
        roles=[EmployeeRoleType.EMPLOYEE],
    )



@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_ACTIVE_STATUSES)
async def test_start_review_rejected_from_every_non_active_status(client, db_session, status):
    employee = await _make_employee(db_session, f"start_{status.value}")
    cycle = await _make_cycle(db_session, employee.id, status)

    await _as_hr_manager(db_session)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [],
            "meetingScheduledAt": datetime(2999, 1, 1).isoformat(),
        },
    )

    assert response.status_code == 409
    assert "ACTIVE" in response.json()["detail"]

    await db_session.refresh(cycle)
    assert cycle.status == status


@pytest.mark.asyncio
async def test_start_review_accepted_from_active(client, db_session):
    employee = await _make_employee(db_session, "start_active")
    cycle = await _make_cycle(db_session, employee.id, CompetencyCycleStatus.ACTIVE)

    await _as_hr_manager(db_session)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [],
            "meetingScheduledAt": datetime(2999, 1, 1).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SELF_ASSESSMENT_PENDING"


@pytest.mark.asyncio
async def test_start_review_cannot_be_called_twice(client, db_session):
    employee = await _make_employee(db_session, "start_twice")
    cycle = await _make_cycle(db_session, employee.id, CompetencyCycleStatus.ACTIVE)

    await _as_hr_manager(db_session)

    first = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [],
            "meetingScheduledAt": datetime(2999, 1, 1).isoformat(),
        },
    )
    assert first.status_code == 200

    second = await client.post(
        f"/competency-cycles/{cycle.id}/start-review",
        json={
            "competencyIds": [],
            "meetingScheduledAt": datetime(2999, 1, 1).isoformat(),
        },
    )
    assert second.status_code == 409



@pytest.mark.asyncio
@pytest.mark.parametrize("status", NON_SELF_ASSESSMENT_PENDING_STATUSES)
async def test_self_assessment_rejected_from_every_other_status(client, db_session, status):
    employee = await _make_employee(db_session, f"self_{status.value}")
    cycle = await _make_cycle(db_session, employee.id, status)

    _as_employee(employee.id)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={"scores": []},
    )

    assert response.status_code == 409

    await db_session.refresh(cycle)
    assert cycle.status == status


@pytest.mark.asyncio
async def test_self_assessment_accepted_from_self_assessment_pending(client, db_session):
    employee = await _make_employee(db_session, "self_ok")
    competency = Competency(name="Python", description="Python", active=True)
    db_session.add(competency)
    await db_session.commit()
    db_session.add(EmployeeCompetency(employee_id=employee.id, competency_id=competency.id))
    await db_session.commit()

    cycle = await _make_cycle(
        db_session, employee.id, CompetencyCycleStatus.SELF_ASSESSMENT_PENDING
    )

    _as_employee(employee.id)

    response = await client.post(
        f"/competency-cycles/{cycle.id}/self-assessment",
        json={"scores": [{"competencyId": competency.id, "score": 4}]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "MANAGER_ASSESSMENT_PENDING"


@pytest.mark.asyncio
async def test_manager_assessment_ignores_cycle_status_if_prerequisites_are_met(client, db_session):
    employee = await _make_employee(db_session, "mgr_gap_emp")
    manager = await _make_employee(db_session, "mgr_gap_mgr")
    employee.manager_id = manager.id
    await db_session.commit()

    competency = Competency(name="Communication", description="Communication", active=True)
    db_session.add(competency)
    await db_session.commit()

    cycle = await _make_cycle(
        db_session,
        employee.id,
        CompetencyCycleStatus.ACTIVE,
        review_started_at=datetime.now(),
    )
    db_session.add(
        CompetencySelfAssessment(cycle_id=cycle.id, competency_id=competency.id, score=3)
    )
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={"scores": [{"competencyId": competency.id, "score": 5}]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REVIEW_PENDING"


@pytest.mark.asyncio
async def test_manager_assessment_rejected_without_review_started(client, db_session):
    employee = await _make_employee(db_session, "mgr_no_review")
    manager = await _make_employee(db_session, "mgr_no_review_mgr")
    employee.manager_id = manager.id
    await db_session.commit()

    cycle = await _make_cycle(db_session, employee.id, CompetencyCycleStatus.ACTIVE)

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={"scores": []},
    )

    assert response.status_code == 409
    assert "not started" in response.json()["detail"]


@pytest.mark.asyncio
async def test_manager_assessment_rejected_when_already_submitted(client, db_session):
    employee = await _make_employee(db_session, "mgr_dup")
    manager = await _make_employee(db_session, "mgr_dup_mgr")
    employee.manager_id = manager.id
    await db_session.commit()

    competency = Competency(name="Ownership", description="Ownership", active=True)
    db_session.add(competency)
    await db_session.commit()

    cycle = await _make_cycle(
        db_session,
        employee.id,
        CompetencyCycleStatus.REVIEW_PENDING,
        review_started_at=datetime.now(),
    )
    db_session.add(
        CompetencySelfAssessment(cycle_id=cycle.id, competency_id=competency.id, score=3)
    )
    db_session.add(
        CompetencyManagerAssessment(cycle_id=cycle.id, competency_id=competency.id, score=4)
    )
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=2,
        employee_id=manager.id,
        username="manager",
        full_name="Manager",
        roles=[EmployeeRoleType.MANAGER],
    )

    response = await client.post(
        f"/competency-cycles/{cycle.id}/manager-assessment",
        json={"scores": [{"competencyId": competency.id, "score": 5}]},
    )

    assert response.status_code == 409
    assert "already submitted" in response.json()["detail"]