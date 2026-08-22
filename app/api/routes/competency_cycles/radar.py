from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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


<<<<<<< HEAD
router = APIRouter()
=======
router = APIRouter(tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)


@router.get(
    "/competency-cycles/{cycle_id}/radar-data",
    response_model=CompetencyRadarData,
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
async def get_radar_data(
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
            selectinload(CompetencyCycle.employee),
            selectinload(CompetencyCycle.focus_competencies),
        )
    )

    cycle = result.scalar_one_or_none()

    if cycle is None:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )

    

    if cycle.review_started_at is None:
        raise HTTPException(
            status_code=409,
            detail="Competency review has not started",
        )

    result = await db.execute(
        select(CompetencyManagerAssessment)
        .where(
            CompetencyManagerAssessment.cycle_id == cycle.id
        )
    )

    manager_assessment_rows = result.scalars().all()

    if not manager_assessment_rows:
        raise HTTPException(
            status_code=409,
            detail="Manager assessment is not completed",
        )

    manager_assessments = {
        item.competency_id: item.score
        for item in manager_assessment_rows
    }

    if (
        current_user.employee_id != cycle.employee_id
        and EmployeeRoleType.HR_MANAGER not in current_user.roles
    ):
        is_direct_manager = (
            EmployeeRoleType.MANAGER in current_user.roles
            and cycle.employee.manager_id == current_user.employee_id
        )

        is_assigned_hrbp = False
        if EmployeeRoleType.HRBP in current_user.roles:
            is_assigned_hrbp = await is_hrbp_of_employee(
                db, current_user.employee_id, cycle.employee_id
            )

        if not is_direct_manager and not is_assigned_hrbp:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

    self_result = await db.execute(
        select(CompetencySelfAssessment).where(
            CompetencySelfAssessment.cycle_id == cycle_id
        )
    )
    self_assessments = {
        item.competency_id: item.score
        for item in self_result.scalars().all()
    }

    labels = []
    employee_scores = []
    manager_scores = []

    for competency in cycle.focus_competencies:
        labels.append(competency.name)

        employee_scores.append(
            float(self_assessments.get(competency.id, 0))
        )

        manager_scores.append(
            float(manager_assessments.get(competency.id, 0))
        )

    return CompetencyRadarData(
        labels=labels,
        employeeScores=employee_scores,
        managerScores=manager_scores,
    )
    
    
