from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import Team
from app.schemas.team import TeamCreate, TeamOut

router = APIRouter(prefix="/teams")


@router.post("", response_model=TeamOut)
async def create_team(
    payload: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("HR_MANAGER")),
):
    team = Team(name=payload.name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("", response_model=list[TeamOut])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("EMPLOYEE", "MANAGER", "HRBP", "HR_MANAGER")),
):
    result = await db.execute(select(Team))
    return result.scalars().all()