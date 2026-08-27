from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.current_user import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.employee import Employee
from app.models.onboarding import Onboarding
from app.schemas.employee import EmployeeDetailOut
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import OnboardingOut

router = APIRouter()


@router.get(
    "/me/onboarding",
    response_model=OnboardingOut,
    responses={
        401: {
            "description": "Unauthorized",
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
        ]
    },
)
async def get_my_onboarding(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(
            Onboarding.employee_id == current_user.employee_id
        )
    )

    onboarding = result.scalar_one_or_none()

    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )

    return onboarding



@router.get(
    "/me/profile",
    response_model=EmployeeDetailOut,
    responses={
        401: {
            "description": "Unauthorized",
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
        ]
    },
)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.team),
            selectinload(Employee.manager),
            selectinload(Employee.direct_reports),
            selectinload(Employee.position),
            selectinload(Employee.onboarding),
            selectinload(Employee.roles),
            selectinload(Employee.competencies)
        )
        .where(
            Employee.employee_id == current_user.employee_id
        )
    )
    employee  = result.scalar_one_or_none()

    if employee  is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )

    return employee 