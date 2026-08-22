from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.models.onboarding import Onboarding, OnboardingStatus
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingOut, StartOnboardingRequest,
    UpdateOnboardingRequest, OnboardingPhaseOut, OnboardingPhaseCreate,
    PhaseStatus, OnboardingActionOut, OnboardingActionCreate,
    OnboardingFeedbackOut, OnboardingFeedbackCreate,
    EmployeeDecisionRequest, EmployeeDecisionResponse, ManagerDecisionRequest,
)
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.core.scope import require_employee_scope


router = APIRouter(prefix="/employees", tags=["Employees"])


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
    },
    openapi_extra={
        "x-allowed-roles": [
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
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
        select(OnboardingTask)
        .join(
            OnboardingPhase,
            OnboardingTask.phase_id == OnboardingPhase.id,
        )
        .where(
            OnboardingPhase.onboarding_id == onboarding.id
        )
    )

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
    
    
