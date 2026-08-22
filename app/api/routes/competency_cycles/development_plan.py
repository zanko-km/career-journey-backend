<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.scope import is_hrbp_of_employee
from app.models import (
    CompetencyCycle,
    DevelopmentPlanItem,
    Employee,
    EmployeeCompetency,
    HrbpTeamAssignment,
    Team,
)
from app.models.user import EmployeeRoleType
from app.schemas.competency_cycle import (
    CompetencyCycleStatus,
)
from app.schemas.development_plan import (
    DevelopmentPlanItemResponse,
    DevelopmentPlanResponse,
    DevelopmentPlanUpsertRequest,
)
from app.schemas.errors import ErrorResponse

router = APIRouter()
=======
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


router = APIRouter(tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)


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
<<<<<<< HEAD
        .options(selectinload(CompetencyCycle.employee))
=======
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
    )

    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(
            status_code=404,
            detail="Competency cycle not found",
        )


    if (
<<<<<<< HEAD
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

=======
        EmployeeRoleType.EMPLOYEE in current_user.roles
        and cycle.employee_id != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)

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
<<<<<<< HEAD
        # HR_MANAGER-authored items are shown in the same "HR side" bucket
        # as HRBP items -- the response only has two buckets (employee vs.
        # HR), and there's no meaningful UI distinction between the two.
        if item.author_role in (EmployeeRoleType.HRBP, EmployeeRoleType.HR_MANAGER)
=======
        if item.author_role == EmployeeRoleType.HRBP
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
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
<<<<<<< HEAD
            "HR_MANAGER",
=======
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
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

<<<<<<< HEAD
    # 2. Employee permission -- only a plain EMPLOYEE (no HRBP/HR_MANAGER
    # role) is restricted to their own cycle. HRBP and HR_MANAGER act on
    # other employees' cycles by design.
    if (
        EmployeeRoleType.EMPLOYEE in current_user.roles
        and EmployeeRoleType.HRBP not in current_user.roles
        and EmployeeRoleType.HR_MANAGER not in current_user.roles
=======
    # 2. Employee permission
    if (
        EmployeeRoleType.EMPLOYEE in current_user.roles
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
        and cycle.employee_id != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

<<<<<<< HEAD
    # 3. Determine author role. HR_MANAGER takes priority over HRBP when a
    # user happens to hold both (same precedence as elsewhere in the app,
    # e.g. meeting organizing), since HR_MANAGER is the unrestricted
    # superset role.
    author_role = (
        EmployeeRoleType.HR_MANAGER
        if EmployeeRoleType.HR_MANAGER in current_user.roles
        else EmployeeRoleType.HRBP
=======
    # 3. Determine author role
    author_role = (
        EmployeeRoleType.HRBP
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
        if EmployeeRoleType.HRBP in current_user.roles
        else EmployeeRoleType.EMPLOYEE
    )

<<<<<<< HEAD
    # 4. HRBP permission -- scoped to assigned teams. HR_MANAGER is
    # unrestricted (consistent with every other HR_MANAGER-vs-HRBP check
    # in the app), so this scope check only applies to genuine HRBP
    # authors.
=======
    # 4. HRBP permission
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
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
<<<<<<< HEAD
    ]
=======
    ]
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
