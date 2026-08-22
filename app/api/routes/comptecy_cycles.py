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
    SelfAssessmentRequest, ManagerAssessmentRequest, CompetencyRadarData, StartReviewRequest)
from app.models.user import EmployeeRoleType
from app.schemas.development_plan import DevelopmentPlanResponse, DevelopmentPlanUpsertRequest, DevelopmentPlanItemResponse
from app.models import DevelopmentPlanItem, Employee, HrbpTeamAssignment, Team
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
        EmployeeRoleType.EMPLOYEE in current_user.roles
        and current_user.employee_id != cycle.employee_id
    ):
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
    
    
def development_plan_item_to_response(item):
    return {
        "id": item.id,
        "competencyId": item.competency_id,
        "authorId": item.author_id,
        "authorRole": item.author_role,
        "completed": item.completed,
        "comment": item.comment,
        "task": item.task,
    }
    
    
@router.get(
    "/competency-cycles/{cycle_id}/idp",
    response_model=DevelopmentPlanResponse,
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden - not owner or not in scope",
            "model": ErrorResponse,
        },
        404: {
            "description": "Competency cycle not found",
            "model": ErrorResponse,
        },
    },
)
async def get_development_plan(
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
    )

    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )


    if (
        EmployeeRoleType.EMPLOYEE in current_user.roles
        and cycle.employee_id != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )


    result = await db.execute(
        select(DevelopmentPlanItem)
        .where(
            DevelopmentPlanItem.cycle_id == cycle_id
        )
    )

    items = result.scalars().all()


    employee_items = [
        item for item in items
        if item.author_role == EmployeeRoleType.EMPLOYEE
    ]

    hrbp_items = [
        item for item in items
        if item.author_role == EmployeeRoleType.HRBP
    ]


    return {
        "employeeItems": [
            development_plan_item_to_response(item)
            for item in employee_items
        ],
        "hrbpItems": [
            development_plan_item_to_response(item)
            for item in hrbp_items
        ],
    }
    
    
@router.post(
    "/competency-cycles/{cycle_id}/idp",
    response_model=list[DevelopmentPlanItemResponse],
    responses={
        400: {
            "description": "Invalid competency"
        },
        403: {
            "description": "Forbidden"
        },
        404: {
            "description": "Competency cycle not found"
        },
        409: {
            "description": "Cycle not accepting IDP"
        },
    },
)
async def submit_development_plan(
    cycle_id: int,
    payload: DevelopmentPlanUpsertRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "EMPLOYEE",
            "HRBP",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    # 1. Get cycle
    result = await db.execute(
        select(CompetencyCycle).where(
            CompetencyCycle.id == cycle_id
        )
    )

    cycle = result.scalar_one_or_none()

    if cycle is None:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )

    # 2. Employee permission
    if (
        EmployeeRoleType.EMPLOYEE in current_user.roles
        and cycle.employee_id != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    # 3. Determine author role
    author_role = (
        EmployeeRoleType.HRBP
        if EmployeeRoleType.HRBP in current_user.roles
        else EmployeeRoleType.EMPLOYEE
    )

    # 4. HRBP permission
    if author_role == EmployeeRoleType.HRBP:
        has_access = await db.execute(
            select(Employee.id)
            .join(Team, Employee.team_id == Team.id)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.team_id == Team.id,
            )
            .where(
                Employee.id == cycle.employee_id,
                HrbpTeamAssignment.hrbp_id
                == current_user.employee_id,
            )
        )

        if has_access.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403,
                detail="HRBP cannot access this employee",
            )

    # 5. Completed cycle cannot change
    if cycle.status == CompetencyCycleStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Cannot submit IDP for completed cycle",
        )

    saved_items = []

    for item in payload.items:

        # 6. Competency assignment check
        assigned = await db.execute(
            select(EmployeeCompetency).where(
                EmployeeCompetency.employee_id
                == cycle.employee_id,
                EmployeeCompetency.competency_id
                == item.competencyId,
            )
        )

        if assigned.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=400,
                detail="Competency is not assigned to this employee",
            )

        # 7. Upsert
        result = await db.execute(
            select(DevelopmentPlanItem).where(
                DevelopmentPlanItem.cycle_id == cycle.id,
                DevelopmentPlanItem.competency_id
                == item.competencyId,
                DevelopmentPlanItem.author_id
                == current_user.employee_id,
                DevelopmentPlanItem.author_role
                == author_role,
            )
        )

        item_db = result.scalar_one_or_none()

        if item_db:
            item_db.comment = item.comment
            item_db.task = item.task
            item_db.completed = item.completed

        else:
            item_db = DevelopmentPlanItem(
                cycle_id=cycle.id,
                competency_id=item.competencyId,
                author_id=current_user.employee_id,
                author_role=author_role,
                comment=item.comment,
                task=item.task,
                completed=item.completed,
            )

            db.add(item_db)

        saved_items.append(item_db)

    await db.commit()

    for item in saved_items:
        await db.refresh(item)

    return [
        development_plan_item_to_response(item)
        for item in saved_items
    ]