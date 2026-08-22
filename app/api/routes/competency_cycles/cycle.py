from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from datetime import datetime, timezone
from app.core.current_user import AuthenticatedUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.core.scope import is_hrbp_of_employee
from sqlalchemy.orm import selectinload
from app.schemas.errors import ErrorResponse
from app.models import CompetencyCycle, EmployeeCompetency, CompetencySelfAssessment, CompetencyManagerAssessment, Competency
from app.schemas.competency_cycle import (
    CompetencyCycleResponse, CompetencyCycleStatus,
    SelfAssessmentRequest, ManagerAssessmentRequest, CompetencyRadarData, StartReviewRequest,
)
from app.models.user import EmployeeRoleType
from app.services.notification import notify_employee


router = APIRouter(tags=["Employees"])


@router.get(
    "/competency-cycles/{cycle_id}",
    response_model=CompetencyCycleResponse,
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden",
            "model": ErrorResponse,
        },
        404: {
            "description": "Not found",
            "model": ErrorResponse,
        },
    },
)
async def get_competency_cycle(
    cycle_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompetencyCycle)
        .where(CompetencyCycle.id == cycle_id)
        .options(
            selectinload(
                CompetencyCycle.focus_competencies
            ),
            selectinload(
                CompetencyCycle.review_started_by
            ),
        )
    )

    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )

    if (
        "EMPLOYEE" in current_user.roles
        and current_user.employee_id != cycle.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    return cycle
@router.post(
    "/competency-cycles/{cycle_id}/start-review",
    response_model=CompetencyCycleResponse,
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden",
            "model": ErrorResponse,
        },
        404: {
            "description": "Not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Conflict",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
        "x-business-rules": [
            "Only allowed while the cycle is ACTIVE.",
            "Sets the deadline (performance review) and the focus competencies for this cycle, "
            "then unlocks self-assessment for the employee.",
        ],
    },
)
async def start_competency_review(
    cycle_id: int,
    payload: StartReviewRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompetencyCycle)
        .where(CompetencyCycle.id == cycle_id)
        .options(
            selectinload(CompetencyCycle.employee),
            selectinload(CompetencyCycle.focus_competencies),
            selectinload(CompetencyCycle.review_started_by),
        )
    )

    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )

    if (
        EmployeeRoleType.HRBP in current_user.roles
        and EmployeeRoleType.HR_MANAGER not in current_user.roles
    ):
        if not await is_hrbp_of_employee(db, current_user.employee_id, cycle.employee_id):
            raise HTTPException(
                status_code=403,
                detail="HRBP can only start a review for employees in assigned teams",
            )

    if cycle.status != CompetencyCycleStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail="Competency review can only be started from ACTIVE status",
        )

    competency_result = await db.execute(
        select(EmployeeCompetency.competency_id).where(
            EmployeeCompetency.employee_id == cycle.employee_id,
            EmployeeCompetency.competency_id.in_(payload.competencyIds),
        )
    )
    valid_competency_ids = set(competency_result.scalars().all())

    if valid_competency_ids != set(payload.competencyIds):
        raise HTTPException(
            status_code=409,
            detail="One or more competencies are not assigned to this employee",
        )

    competencies_result = await db.execute(
        select(Competency).where(Competency.id.in_(payload.competencyIds))
    )
    cycle.focus_competencies = list(competencies_result.scalars().all())

    cycle.review_started_at = datetime.now(timezone.utc)
    cycle.review_started_by_id = current_user.employee_id
    cycle.focus_ends_at = payload.focusEndsAt
    cycle.status = CompetencyCycleStatus.SELF_ASSESSMENT_PENDING

    await notify_employee(
        db,
        employee_id=cycle.employee_id,
        type="PERFORMANCE_REVIEW_DEADLINE_SET",
        message="Your performance review has started. Please submit your self-assessment.",
        reference_type="COMPETENCY_CYCLE",
        reference_id=cycle.id,
    )

    await db.commit()
    await db.refresh(cycle)

    result = await db.execute(
        select(CompetencyCycle)
        .where(CompetencyCycle.id == cycle.id)
        .options(
            selectinload(CompetencyCycle.focus_competencies),
            selectinload(CompetencyCycle.review_started_by),
        )
    )

    return result.scalar_one()
