from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import (
    Meeting,
    MeetingParticipant,
    Employee,
    HrbpTeamAssignment, MeetingStatus,
    Team, EmployeeRole,
)
from app.schemas.meeting import MeetingResponse, MeetingCreate, MeetingRespondRequest, MeetingConfirmHeldRequest
from app.schemas.errors import ErrorResponse


router = APIRouter(prefix="/meetings")


@router.get(
    "",
    response_model=list[MeetingResponse],
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
async def list_meetings(
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

    visible_employee_ids = [
        current_user.employee_id
    ]


    if "MANAGER" in current_user.roles:

        result = await db.execute(
            select(Employee.id).where(
                Employee.manager_id == current_user.employee_id
            )
        )

        team_employee_ids = result.scalars().all()

        visible_employee_ids.extend(
            team_employee_ids
        )


    if "HRBP" in current_user.roles:

        result = await db.execute(
            select(Employee.id)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.team_id == Employee.team_id,
            )
            .where(
                HrbpTeamAssignment.hrbp_id
                == current_user.employee_id
            )
        )

        hrbp_employee_ids = result.scalars().all()

        visible_employee_ids.extend(
            hrbp_employee_ids
        )


    if "HR_MANAGER" in current_user.roles:

        result = await db.execute(
            select(Employee.id)
        )

        all_employee_ids = result.scalars().all()

        visible_employee_ids = all_employee_ids


    result = await db.execute(
        select(Meeting)
        .join(
            MeetingParticipant,
            MeetingParticipant.meeting_id == Meeting.id,
            isouter=True,
        )
        .where(
            or_(
                MeetingParticipant.employee_id.in_(
                    visible_employee_ids
                ),
                Meeting.organizer_id == current_user.employee_id,
            )
        )
        .options(
            selectinload(Meeting.participants)
            .selectinload(MeetingParticipant.employee),
            selectinload(Meeting.organizer),
        )
    )


    meetings = result.scalars().unique().all()

    return meetings
@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
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
)
async def get_meeting(
    meeting_id: int,
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
        select(Meeting)
        .where(
            Meeting.id == meeting_id
        )
        .options(
            selectinload(Meeting.participants)
            .selectinload(MeetingParticipant.employee),
            selectinload(Meeting.organizer),
        )
    )

    meeting = result.scalar_one_or_none()


    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found"
        )


    allowed = False


    if meeting.organizer_id == current_user.employee_id:
        allowed = True


    if not allowed:
        participant_ids = [
            p.employee_id
            for p in meeting.participants
        ]

        if current_user.employee_id in participant_ids:
            allowed = True


    if (
        not allowed
        and "MANAGER" in current_user.roles
    ):
        if meeting.employee.manager_id == current_user.employee_id:
            allowed = True


    if (
        not allowed
        and "HR_MANAGER" in current_user.roles
    ):
        allowed = True


    if (
        not allowed
        and "HRBP" in current_user.roles
    ):
        hrbp_employee = await db.execute(
            select(Employee.id)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.team_id == Employee.team_id,
            )
            .where(
                HrbpTeamAssignment.hrbp_id
                == current_user.employee_id,
                Employee.id == meeting.employee_id,
            )
        )

        if hrbp_employee.scalar_one_or_none():
            allowed = True


    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )


    return meeting
