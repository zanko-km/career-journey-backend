from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.current_user import AuthenticatedUser
from app.core.permissions import require_roles

from app.models import Competency

from app.schemas.competency import CompetencyResponse, CompetencyCreate
from app.schemas.errors import ErrorResponse


router = APIRouter(
    prefix="/competencies",
    tags=["Competencies"],
)


@router.get(
    "",
    response_model=list[CompetencyResponse],
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
)
async def list_competencies(
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Competency)
        .where(
            Competency.active.is_(True)
        )
        .order_by(
            Competency.name
        )
    )

    return result.scalars().all()


@router.post(
    "",
    response_model=CompetencyResponse,
    status_code=status.HTTP_201_CREATED,
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
    },
)
async def create_competency(
    payload: CompetencyCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):

    existing = await db.execute(
        select(Competency).where(
            Competency.name == payload.name
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Competency already exists",
        )


    competency = Competency(
        name=payload.name,
        description=payload.description,
        active=True,
    )

    db.add(competency)

    await db.commit()
    await db.refresh(competency)

    return competency