from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from sqlalchemy.orm import selectinload
from app.models.onboarding import Onboarding, OnboardingStatus
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingOut, StartOnboardingRequest,
    UpdateOnboardingRequest, OnboardingPhaseOut, OnboardingPhaseCreate,
    PhaseStatus, OnboardingActionOut, OnboardingActionCreate,
    OnboardingFeedbackOut, OnboardingFeedbackCreate,
    EmployeeDecisionRequest, EmployeeDecisionResponse, ManagerDecisionRequest,
)
from datetime import timedelta
from app.core.scope import require_employee_scope


router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get(
    "/{employee_id}/onboarding",
    response_model=OnboardingOut,
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
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def get_employee_onboarding(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
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
            .options(
                selectinload(Onboarding.buddy),
                selectinload(Onboarding.development_plan),
            )
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

    return onboarding
@router.post(
    "/{employee_id}/onboarding",
    response_model=OnboardingOut,
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
    },
)
async def start_employee_onboarding(
    employee_id: int,
    payload: StartOnboardingRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )


    result = await db.execute(
        select(Onboarding).where(
            Onboarding.employee_id == employee_id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Onboarding already exists",
        )


    end_date = (
        payload.start_date +
        timedelta(
            days=30 * payload.duration_months
        )
    )


    onboarding = Onboarding(
        employee_id=employee_id,
        start_date=payload.start_date,
        end_date=end_date,
        duration_months=payload.duration_months,
        buddy_id=payload.buddy_id,
        current_phase_number=1,
    )


    db.add(onboarding)

    await db.commit()

    await db.refresh(onboarding)


    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(
            Onboarding.id == onboarding.id
        )
    )

    return result.scalar_one()
@router.patch(
    "/{employee_id}/onboarding",
    response_model=OnboardingOut,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def update_employee_onboarding(
    employee_id: int,
    payload: UpdateOnboardingRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
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


    if onboarding.status != OnboardingStatus.NOT_STARTED:
        raise HTTPException(
            status_code=409,
            detail="Cannot update started onboarding",
        )


    if payload.start_date:
        onboarding.start_date = payload.start_date

    if payload.duration_months:
        onboarding.duration_months = payload.duration_months

    if payload.buddy_id:
        onboarding.buddy_id = payload.buddy_id


    await db.commit()

    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(
            Onboarding.id == onboarding.id
        )
    )

    onboarding = result.scalar_one()

    return onboarding
