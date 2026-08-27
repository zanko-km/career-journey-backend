<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
<<<<<<< HEAD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

=======
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import (
<<<<<<< HEAD
<<<<<<< HEAD
    Employee,
    HrbpTeamAssignment,
    Meeting,
    MeetingParticipant,
)
from app.schemas.errors import ErrorResponse
from app.schemas.meeting import (
    MeetingResponse,
)

router = APIRouter(prefix="/meetings")
=======
=======
    Employee,
    HrbpTeamAssignment,
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    Meeting,
    MeetingParticipant,
)
from app.schemas.errors import ErrorResponse
from app.schemas.meeting import (
    MeetingResponse,
)

<<<<<<< HEAD
router = APIRouter(prefix="/meetings", tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
router = APIRouter(prefix="/meetings")
>>>>>>> 2abb2b4 (fixing issues with swagger and adding more test to performance testing)


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
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
        422: {
            "description": "Validation Error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-query-params": [
            "withinDays (optional, int >= 1): only return meetings scheduled "
            "between now and now + withinDays days. Omit to get the full, "
            "unfiltered list (existing/default behaviour).",
        ],
<<<<<<< HEAD
=======
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
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
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    within_days: int | None = Query(
        default=None,
        alias="withinDays",
        ge=1,
        description=(
            "Only return meetings scheduled within the next N days "
            "(e.g. withinDays=30 for 'next month'). Omitted = no filtering."
        ),
    ),
<<<<<<< HEAD
=======
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
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


<<<<<<< HEAD
<<<<<<< HEAD
    query = (
=======
    result = await db.execute(
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
    query = (
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
    if within_days is not None:
        now = datetime.now()

        query = query.where(
            Meeting.scheduled_at >= now,
            Meeting.scheduled_at <= now + timedelta(days=within_days),
        )

    result = await db.execute(query)

<<<<<<< HEAD
=======
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)

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
<<<<<<< HEAD
<<<<<<< HEAD
    ) and meeting.employee.manager_id == current_user.employee_id:
        allowed = True
=======
    ):
        if meeting.employee.manager_id == current_user.employee_id:
            allowed = True
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
    ) and meeting.employee.manager_id == current_user.employee_id:
        allowed = True
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)


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


<<<<<<< HEAD
<<<<<<< HEAD
    return meeting
=======
    return meeting
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
=======
    return meeting
>>>>>>> 7298a79 (add tests for checking employee actions coverage and fixing bugs)
