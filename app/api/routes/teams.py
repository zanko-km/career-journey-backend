from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.scope import require_team_scope
from app.core.current_user import AuthenticatedUser, get_current_user
from app.models import Team, Employee, HrbpTeamAssignment
from app.schemas.team import TeamCreate, TeamOut, TeamEmployeeOut, HrbpTeamAssignmentCreate, HrbpTeamAssignmentOut
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
    _scope: AuthenticatedUser = Depends(require_team_scope("team_id")),
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
    _scope: AuthenticatedUser = Depends(require_team_scope("team_id")),
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
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
):
    query = select(Team).options(
        selectinload(Team.department),
        selectinload(Team.team_manager),
        selectinload(Team.hrbps)
    )

    if "HR_MANAGER" not in current_user.roles:
        if "HRBP" in current_user.roles:
            query = query.join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.team_id == Team.id,
            ).where(HrbpTeamAssignment.hrbp_id == current_user.employee_id)
        elif "MANAGER" in current_user.roles:
            query = query.where(Team.team_manager_id == current_user.employee_id)

    result = await db.execute(query)

    return result.scalars().all()


@router.post(
    "/{team_id}/hrbps",
    response_model=HrbpTeamAssignmentOut,
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
            "HR_MANAGER",
        ]
    },
)
async def assign_hrbp_to_team(
    team_id: int,
    payload: HrbpTeamAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("HR_MANAGER")),
):
    if payload.team_id != team_id:
        raise HTTPException(
            status_code=422,
            detail="teamId in body must match the URL",
        )

    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    hrbp = await db.get(Employee, payload.hrbp_id)
    if hrbp is None:
        raise HTTPException(status_code=404, detail="HRBP employee not found")

    existing = (
        await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == payload.hrbp_id,
                HrbpTeamAssignment.team_id == team_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="HRBP is already assigned to this team",
        )

    assignment = HrbpTeamAssignment(
        hrbp_id=payload.hrbp_id,
        team_id=team_id,
    )
    db.add(assignment)

    await db.commit()
    await db.refresh(assignment)

    return assignment


@router.delete(
    "/{team_id}/hrbps/{hrbp_id}",
    status_code=204,
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
            "HR_MANAGER",
        ]
    },
)
async def unassign_hrbp_from_team(
    team_id: int,
    hrbp_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("HR_MANAGER")),
):
    existing = (
        await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == hrbp_id,
                HrbpTeamAssignment.team_id == team_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await db.delete(existing)
    await db.commit()