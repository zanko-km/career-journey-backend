from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import Team, Employee, HrbpTeamAssignment
from app.schemas.team import TeamCreate, TeamOut, TeamEmployeeOut
from sqlalchemy.orm import selectinload
from app.schemas.errors import ErrorResponse

router = APIRouter(prefix="/teams")

@router.post(
    "",
    response_model=TeamOut,
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
        409: {
            "description": "Conflict",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HR_MANAGER",
        ]
    },
)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("HR_MANAGER")),
):
    team = Team(
        name=payload.name,
        department_id=payload.department_id,
        team_manager_id=payload.team_manager_id,
    )

    db.add(team)

    await db.commit()

    result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.department),
            selectinload(Team.team_manager),
            selectinload(Team.hrbps)
        )
        .where(Team.id == team.id)
    )

    return result.scalar_one()

@router.get(
    "/{team_id}",
    response_model=TeamOut,
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
        ]
    },
)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(
        require_roles(
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
):
    result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.department),

            selectinload(Team.team_manager)
            .selectinload(Employee.position),

            selectinload(Team.hrbps)
            .selectinload(Employee.position),
        )
        .where(Team.id == team_id)
    )

    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team


@router.get(
    "/{team_id}/employees",
    response_model=list[TeamEmployeeOut],
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
            "description": "Not found",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ]
    },
)
async def get_team_employees(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(
        require_roles(
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
):
    team_result = await db.execute(
        select(Team.id).where(Team.id == team_id)
    )

    team_exists = team_result.scalar_one_or_none()

    if team_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.position),
            selectinload(Employee.onboarding),
        )
        .where(Employee.team_id == team_id)
    )

    employees = result.scalars().all()

    return [
        TeamEmployeeOut(
            id=employee.id,
            full_name=employee.full_name,
            nickname=employee.nickname,
            job_title=employee.job_title,
            status=employee.status.value,
            career_stage=employee.career_stage.value,
            onboarding_phase=(
                employee.onboarding.current_phase_number
                if employee.onboarding
                else None
            ),
        )
        for employee in employees
    ]


@router.get(
    "",
    response_model=list[TeamOut],
    responses={
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ]
    },
)
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _user=Depends(
        require_roles(
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
):
    result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.department),
            selectinload(Team.team_manager),
            selectinload(Team.hrbps)
        )
    )

    return result.scalars().all()