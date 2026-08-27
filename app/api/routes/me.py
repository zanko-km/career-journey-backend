from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.current_user import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.employee import Employee
<<<<<<< HEAD
<<<<<<< HEAD
from app.models.employee_role import EmployeeRole
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.onboarding import Onboarding
from app.models.team import Team
from app.schemas.employee import EmployeeDetailOut, EmployeeSummary, TeamOut
=======
from app.models.onboarding import Onboarding
from app.schemas.employee import EmployeeDetailOut
>>>>>>> 1385b82 (Feat: add me/profile endpoint)
=======
from app.models.employee_role import EmployeeRole
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.onboarding import Onboarding
from app.models.team import Team
from app.schemas.employee import EmployeeDetailOut, EmployeeSummary, TeamOut
>>>>>>> 0e1fb74 (updating profile visibility for manager HR and HRBP)
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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 0e1fb74 (updating profile visibility for manager HR and HRBP)
    return employee


@router.get(
    "/me/managed-employees",
    response_model=list[EmployeeSummary],
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HR_MANAGER",
        ]
    },
)
async def get_my_employees(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee)
        .where(
            Employee.manager_id == current_user.employee_id
        )
    )

    employees = result.scalars().all()

    return employees


@router.get(
    "/me/assigned-teams",
    response_model=list[TeamOut],
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HR_MANAGER",
        ]
    },
)
async def get_my_teams(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Team)
        .join(
            HrbpTeamAssignment,
            HrbpTeamAssignment.team_id == Team.id
        )
        .where(
            HrbpTeamAssignment.hrbp_id == current_user.employee_id
        )
    )

    teams = result.scalars().all()

    return teams


@router.get(
    "/me/managed-hrbps",
    response_model=list[EmployeeSummary],
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
<<<<<<< HEAD
<<<<<<< HEAD
=======
            "MANAGER",
>>>>>>> 0e1fb74 (updating profile visibility for manager HR and HRBP)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
            "HR_MANAGER",
        ]
    },
)
async def get_my_hrbps(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee)
        .join(Employee.roles)
        .where(
            Employee.manager_id == current_user.employee_id,
            EmployeeRole.role == "HRBP",
        )
    )

    hrbps = result.scalars().all()

<<<<<<< HEAD
    return hrbps
=======
    return employee 
>>>>>>> 1385b82 (Feat: add me/profile endpoint)
=======
    return hrbps
>>>>>>> 0e1fb74 (updating profile visibility for manager HR and HRBP)
