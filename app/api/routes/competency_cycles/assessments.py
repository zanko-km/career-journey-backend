from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from sqlalchemy.orm import selectinload
from app.schemas.errors import ErrorResponse
from app.models import CompetencyCycle, EmployeeCompetency, CompetencySelfAssessment, CompetencyManagerAssessment, Competency
from app.schemas.competency_cycle import (
    CompetencyCycleResponse, CompetencyCycleStatus,
    SelfAssessmentRequest, ManagerAssessmentRequest, CompetencyRadarData, StartReviewRequest,
)
from app.models.user import EmployeeRoleType
from app.models import DevelopmentPlanItem, Employee, HrbpTeamAssignment, Team


router = APIRouter()


@router.post(
    "/competency-cycles/{cycle_id}/self-assessment",
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
)
async def submit_self_assessment(
    cycle_id: int,
    payload: SelfAssessmentRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles("EMPLOYEE")
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompetencyCycle)
        .where(CompetencyCycle.id == cycle_id)
        .options(
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

    if current_user.employee_id != cycle.employee_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    if cycle.status != CompetencyCycleStatus.SELF_ASSESSMENT_PENDING:
        raise HTTPException(
            status_code=409,
            detail="Self-assessment is not available",
        )

    competency_ids = {
        item.competencyId
        for item in payload.scores
    }

    result = await db.execute(
        select(EmployeeCompetency.competency_id)
        .where(
            EmployeeCompetency.employee_id == cycle.employee_id,
            EmployeeCompetency.competency_id.in_(competency_ids),
        )
    )

    valid_competency_ids = set(result.scalars().all())

    if valid_competency_ids != competency_ids:
        raise HTTPException(
            status_code=409,
            detail="Invalid competency",
        )

    for item in payload.scores:
        db.add(
            CompetencySelfAssessment(
                cycle_id=cycle.id,
                competency_id=item.competencyId,
                score=item.score,
            )
        )

    cycle.status = CompetencyCycleStatus.MANAGER_ASSESSMENT_PENDING

    await db.commit()
    await db.refresh(cycle)

    return cycle
@router.post(
    "/competency-cycles/{cycle_id}/manager-assessment",
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
)
async def submit_manager_assessment(
    cycle_id: int,
    payload: ManagerAssessmentRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "MANAGER",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CompetencyCycle)
        .where(
            CompetencyCycle.id == cycle_id
        )
        .options(
            selectinload(
                CompetencyCycle.employee
            ),
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
        EmployeeRoleType.MANAGER in current_user.roles
        and cycle.employee.manager_id != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only direct manager can submit assessment",
        )


    if cycle.review_started_at is None:
        raise HTTPException(
            status_code=409,
            detail="Competency review has not started",
        )


    result = await db.execute(
        select(CompetencySelfAssessment)
        .where(
            CompetencySelfAssessment.cycle_id == cycle.id
        )
    )

    self_assessments = result.scalars().all()

    if not self_assessments:
        raise HTTPException(
            status_code=409,
            detail="Employee self-assessment is not completed",
        )


    competency_ids = {
        item.competencyId
        for item in payload.scores
    }


    self_competency_ids = {
        item.competency_id
        for item in self_assessments
    }

    if not competency_ids.issubset(self_competency_ids):
        raise HTTPException(
            status_code=409,
            detail="Invalid competency",
        )


    result = await db.execute(
        select(CompetencyManagerAssessment.competency_id)
        .where(
            CompetencyManagerAssessment.cycle_id == cycle.id
        )
    )

    existing_ids = set(result.scalars().all())

    if existing_ids:
        raise HTTPException(
            status_code=409,
            detail="Manager assessment already submitted",
        )


    for item in payload.scores:
        db.add(
            CompetencyManagerAssessment(
                cycle_id=cycle.id,
                competency_id=item.competencyId,
                score=item.score,
            )
        )


    cycle.status = CompetencyCycleStatus.REVIEW_PENDING


    await db.commit()
    await db.refresh(cycle)

    return cycle
