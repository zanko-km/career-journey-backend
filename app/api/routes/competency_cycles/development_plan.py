from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.schemas.errors import ErrorResponse
from app.models import CompetencyCycle, EmployeeCompetency, CompetencySelfAssessment, CompetencyManagerAssessment, Competency
from app.schemas.competency_cycle import (
    CompetencyCycleResponse, CompetencyCycleStatus,
    SelfAssessmentRequest, ManagerAssessmentRequest, CompetencyRadarData, StartReviewRequest,
)
from app.models.user import EmployeeRoleType
from app.schemas.development_plan import DevelopmentPlanResponse, DevelopmentPlanUpsertRequest, DevelopmentPlanItemResponse
from app.models import DevelopmentPlanItem, Employee, HrbpTeamAssignment, Team


router = APIRouter()


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
