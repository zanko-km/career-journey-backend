from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.current_user import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import Employee
from app.models.hrbp_team_assignment import HrbpTeamAssignment

MAX_HIERARCHY_DEPTH = 20  # safety cap against cyclic manager_id data


async def is_manager_of(db: AsyncSession, manager_employee_id: int, target_employee_id: int) -> bool:
    if manager_employee_id == target_employee_id:
        return False

    current = await db.get(Employee, target_employee_id)
    depth = 0
    while current is not None and current.manager_id is not None and depth < MAX_HIERARCHY_DEPTH:
        if current.manager_id == manager_employee_id:
            return True
        current = await db.get(Employee, current.manager_id)
        depth += 1
    return False


async def is_hrbp_of_employee(db: AsyncSession, hrbp_employee_id: int, target_employee_id: int) -> bool:
    target = await db.get(Employee, target_employee_id)
    if target is None or target.team_id is None:
        return False

    assignment = (
        await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == hrbp_employee_id,
                HrbpTeamAssignment.team_id == target.team_id,
            )
        )
    ).scalar_one_or_none()
    return assignment is not None


async def is_hrbp_of_team(db: AsyncSession, hrbp_employee_id: int, team_id: int) -> bool:
    assignment = (
        await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == hrbp_employee_id,
                HrbpTeamAssignment.team_id == team_id,
            )
        )
    ).scalar_one_or_none()
    return assignment is not None


def require_employee_scope(param_name: str = "employeeId"):

    async def checker(
        employee_id: int = Path(..., alias=param_name),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        if employee_id == current_user.employee_id:
            return current_user

        if "HR_MANAGER" in current_user.roles:
            return current_user

        if "HRBP" in current_user.roles:
            if await is_hrbp_of_employee(db, current_user.employee_id, employee_id):
                return current_user

        if "MANAGER" in current_user.roles:
            if await is_manager_of(db, current_user.employee_id, employee_id):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this employee's data",
        )

    return checker


def require_team_scope(param_name: str = "teamId"):

    async def checker(
        team_id: int = Path(..., alias=param_name),
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> AuthenticatedUser:
        if "HR_MANAGER" in current_user.roles:
            return current_user

        if "HRBP" in current_user.roles:
            if await is_hrbp_of_team(db, current_user.employee_id, team_id):
                return current_user

        if "MANAGER" in current_user.roles:
            from app.models import Team  # local import to avoid cycles

            team = await db.get(Team, team_id)
            if team is not None and team.team_manager_id == current_user.employee_id:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this team's data",
        )

    return checker