<<<<<<< HEAD
<<<<<<< HEAD
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.scope import require_employee_scope
from app.models.employee import Employee
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.onboarding import Onboarding
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingActionCreate,
    OnboardingActionOut,
)

router = APIRouter(prefix="/employees",)
=======
from fastapi import APIRouter, Depends, HTTPException, status
=======
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.scope import require_employee_scope
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingActionCreate,
    OnboardingActionOut,
)

<<<<<<< HEAD
router = APIRouter(prefix="/employees", tags=["Employees"])
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
router = APIRouter(prefix="/employees",)
>>>>>>> 2abb2b4 (fixing issues with swagger and adding more test to performance testing)


@router.get(
    "/{employee_id}/onboarding/actions",
    response_model=list[OnboardingActionOut],
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
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
        422: {
            "description": "Validation Error",
            "model": ErrorResponse,
        },
<<<<<<< HEAD
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    },
    openapi_extra={
        "x-allowed-roles": [
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
        "x-query-params": [
            "withinDays (optional, int >= 1): only return tasks due between "
            "today and today + withinDays days. Omit to get the full, "
            "unfiltered list (existing/default behaviour).",
        ],
<<<<<<< HEAD
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    },
)
async def get_employee_onboarding_actions(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    within_days: int | None = Query(
        default=None,
        alias="withinDays",
        ge=1,
        description=(
            "Only return tasks due within the next N days "
            "(e.g. withinDays=30 for 'next month'). Omitted = no filtering."
        ),
    ),
<<<<<<< HEAD
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
):

    result = await db.execute(
        select(Onboarding)
        .where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = result.scalar_one_or_none()


    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )


<<<<<<< HEAD
<<<<<<< HEAD
    task_query = (
=======
    result = await db.execute(
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
    task_query = (
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
        select(OnboardingTask)
        .join(
            OnboardingPhase,
            OnboardingTask.phase_id == OnboardingPhase.id,
        )
        .where(
            OnboardingPhase.onboarding_id == onboarding.id
        )
    )

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    if within_days is not None:
        today = date.today()

        task_query = task_query.where(
            OnboardingTask.due_date.is_not(None),
            OnboardingTask.due_date >= today,
            OnboardingTask.due_date <= today + timedelta(days=within_days),
        )

    result = await db.execute(task_query)

<<<<<<< HEAD
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    tasks = result.scalars().all()


    response = []


    for task in tasks:

        result = await db.execute(
            select(Employee)
            .where(
                Employee.id == task.assigned_by
            )
        )

        creator = result.scalar_one()


        response.append(
            OnboardingActionOut(
                id=task.id,
                phaseId=task.phase_id,
                title=task.title,
                description=getattr(
                    task,
                    "description",
                    None
                ),
                dueDate=task.due_date,
                status=task.status,
                createdBy=creator,
            )
        )


    return response
@router.post(
    "/{employee_id}/onboarding/actions",
    response_model=OnboardingActionOut,
    status_code=201,
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
        422: {
            "description": "Validation Error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
<<<<<<< HEAD
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "MANAGER may only create tasks for their own direct reports.",
            "HRBP may only create tasks for employees in their assigned "
            "teams (used as the fallback path when the manager misses the "
            "same-day deadline; see "
            "POST /employees/{employee_id}/onboarding/check-month2-tasks-deadline "
            "-- which only ever notifies HRBPs already assigned to the "
            "employee's team, so this scoping does not break that flow).",
            "HR_MANAGER is unrestricted.",
        ],
=======
            "HRBP",
            "HR_MANAGER",
        ],
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
    },
)
async def create_employee_onboarding_action(
    employee_id: int,
    payload: OnboardingActionCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(
<<<<<<< HEAD
            "MANAGER",
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):

<<<<<<< HEAD
    employee_result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = employee_result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if (
        "MANAGER" in current_user.roles
        and "HRBP" not in current_user.roles
        and "HR_MANAGER" not in current_user.roles
    ):
        if employee.manager_id != current_user.employee_id:
            raise HTTPException(
                status_code=403,
                detail="Only the employee's direct manager can create this task",
            )

    if (
        "HRBP" in current_user.roles
        and "HR_MANAGER" not in current_user.roles
    ):
        assignment_result = await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == current_user.employee_id,
                HrbpTeamAssignment.team_id == employee.team_id,
            )
        )

        if assignment_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403,
                detail="HRBP can only create tasks for employees in assigned teams",
            )

=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
    result = await db.execute(
        select(Onboarding)
        .where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = result.scalar_one_or_none()


    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )


    result = await db.execute(
        select(OnboardingPhase)
        .where(
            OnboardingPhase.id == payload.phase_id,
            OnboardingPhase.onboarding_id == onboarding.id,
        )
    )

    phase = result.scalar_one_or_none()


    if phase is None:
        raise HTTPException(
            status_code=404,
            detail="Phase not found",
        )


    task = OnboardingTask(
        phase_id=payload.phase_id,
        assigned_by=current_user.employee_id,
        assigned_to=employee_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
    )


    db.add(task)

    await db.commit()
    await db.refresh(task)


    result = await db.execute(
        select(Employee)
        .where(
            Employee.id == task.assigned_by
        )
    )

    creator = result.scalar_one()


    return OnboardingActionOut(
        id=task.id,
        phaseId=task.phase_id,
        title=task.title,
        description=task.description,
        dueDate=task.due_date,
        status=task.status,
        createdBy=creator,
<<<<<<< HEAD
<<<<<<< HEAD
    )
=======
    )
    
    
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
=======
    )
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
