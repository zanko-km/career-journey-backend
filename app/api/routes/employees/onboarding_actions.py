from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/employees",)


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
        422: {
            "description": "Validation Error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
        "x-query-params": [
            "withinDays (optional, int >= 1): only return tasks due between "
            "today and today + withinDays days. Omit to get the full, "
            "unfiltered list (existing/default behaviour).",
        ],
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
    within_days: int | None = Query(
        default=None,
        alias="withinDays",
        ge=1,
        description=(
            "Only return tasks due within the next N days "
            "(e.g. withinDays=30 for 'next month'). Omitted = no filtering."
        ),
    ),
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


    task_query = (
        select(OnboardingTask)
        .join(
            OnboardingPhase,
            OnboardingTask.phase_id == OnboardingPhase.id,
        )
        .where(
            OnboardingPhase.onboarding_id == onboarding.id
        )
    )

    if within_days is not None:
        today = date.today()

        task_query = task_query.where(
            OnboardingTask.due_date.is_not(None),
            OnboardingTask.due_date >= today,
            OnboardingTask.due_date <= today + timedelta(days=within_days),
        )

    result = await db.execute(task_query)

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
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def create_employee_onboarding_action(
    employee_id: int,
    payload: OnboardingActionCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
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
    )