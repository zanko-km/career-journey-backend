<<<<<<< HEAD
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
=======
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import (
    Employee,
    EmployeeRole,
    HrbpTeamAssignment,
    Meeting,
    MeetingParticipant,
    MeetingStatus,
    Team,
)
<<<<<<< HEAD
=======
from app.schemas.meeting import MeetingResponse, MeetingCreate, MeetingRespondRequest, MeetingConfirmHeldRequest
from app.schemas.errors import ErrorResponse
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)
from app.models.meeting_participant import MeetingResponseStatus
from app.models.user import EmployeeRoleType
from app.schemas.errors import ErrorResponse
from app.schemas.meeting import (
    MeetingConfirmHeldRequest,
    MeetingCreate,
    MeetingRespondRequest,
    MeetingResponse,
)
from app.services.notification import notify_employee

<<<<<<< HEAD
router = APIRouter(prefix="/meetings")
=======

router = APIRouter(prefix="/meetings", tags=["Employees"])
>>>>>>> 9218357 (refactor: split competency_cycles.py and meetings.py into route packages)


async def _can_organize_downward(
    db: AsyncSession,
    current_user: AuthenticatedUser,
    employee: Employee,
) -> bool:

    if EmployeeRoleType.HR_MANAGER in current_user.roles:
        return True

    if EmployeeRoleType.MANAGER in current_user.roles:
        if employee.manager_id == current_user.employee_id:
            return True

    if EmployeeRoleType.HRBP in current_user.roles:
        assignment_result = await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == current_user.employee_id,
                HrbpTeamAssignment.team_id == employee.team_id,
            )
        )
        if assignment_result.scalar_one_or_none() is not None:
            return True

    return False
async def _upward_allowed_target_ids(
    db: AsyncSession,
    employee: Employee,
) -> set[int]:
    
    allowed_ids: set[int] = set()

    if employee.manager_id is not None:
        allowed_ids.add(employee.manager_id)

    if employee.team_id is not None:
        team = await db.get(Team, employee.team_id)

        if team is not None and team.team_manager_id is not None:
            allowed_ids.add(team.team_manager_id)

        hrbp_result = await db.execute(
            select(HrbpTeamAssignment.hrbp_id).where(
                HrbpTeamAssignment.team_id == employee.team_id
            )
        )
        allowed_ids.update(hrbp_result.scalars().all())

    hr_manager_result = await db.execute(
        select(EmployeeRole.employee_id).where(
            EmployeeRole.role == EmployeeRoleType.HR_MANAGER.value
        )
    )
    allowed_ids.update(hr_manager_result.scalars().all())

    allowed_ids.discard(employee.id)

    return allowed_ids
@router.post(
    "",
    response_model=MeetingResponse,
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
    },
)
async def create_meeting(
    payload: MeetingCreate,
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
    employee = await db.get(
        Employee,
        payload.employee_id
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    allowed = await _can_organize_downward(db, current_user, employee)

    if not allowed and employee.id == current_user.employee_id:
        allowed_target_ids = await _upward_allowed_target_ids(db, employee)

        if payload.participant_ids and set(payload.participant_ids).issubset(allowed_target_ids):
            allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to organize a meeting for this employee/participants"
        )


    if payload.scheduled_at < datetime.now() - timedelta(seconds=5):
        raise HTTPException(
            status_code=422,
            detail="Meeting time must be in the future"
        )


    if len(payload.participant_ids) != len(set(payload.participant_ids)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate participants are not allowed"
        )


    meeting = Meeting(
        organizer_id=current_user.employee_id,
        employee_id=payload.employee_id,
        scheduled_at=payload.scheduled_at,
        notes=payload.notes,
        onboarding_id=payload.onboarding_id,
        onboarding_month=payload.onboarding_month,
        status=MeetingStatus.PROPOSED,
    )

    db.add(meeting)

    await db.flush()


    for participant_id in payload.participant_ids:
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=participant_id,
        )

        db.add(participant)

        await notify_employee(
            db,
            employee_id=participant_id,
            type="MEETING_SCHEDULED",
            message=f"A meeting has been scheduled for {payload.scheduled_at.isoformat()}. Please confirm your attendance.",
            reference_type="MEETING",
            reference_id=meeting.id,
        )

    if current_user.employee_id not in payload.participant_ids:
        organizer_participant = MeetingParticipant(
            meeting_id=meeting.id,
            employee_id=current_user.employee_id,
            response_status=MeetingResponseStatus.CONFIRMED,
        )

        db.add(organizer_participant)


    await db.commit()
    result = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting.id)
        .options(
            selectinload(Meeting.participants)
            .selectinload(MeetingParticipant.employee),
            selectinload(Meeting.organizer),
        )
    )

    meeting = result.scalar_one()

    return meeting
@router.post(
    "/{meeting_id}/respond",
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
        409: {
            "description": "Conflict",
            "model": ErrorResponse,
        },
    },
)
async def respond_meeting(
    meeting_id: int,
    payload: MeetingRespondRequest,
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
            .where(Meeting.id == meeting_id)
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
            
        participant = next(
            (
                p
                for p in meeting.participants
                if p.employee_id == current_user.employee_id
            ),
            None,
        )

        if not participant:
            raise HTTPException(
                status_code=403,
                detail="Only participants can respond"
            )
            
        if participant.response_status != MeetingResponseStatus.PENDING:
            raise HTTPException(
                status_code=409,
                detail="Already responded"
            )
            
            
        participant.response_status = payload.response

        await db.commit()
        
        
        result = await db.execute(
            select(Meeting)
            .where(Meeting.id == meeting.id)
            .options(
                selectinload(Meeting.participants)
                .selectinload(MeetingParticipant.employee),
                selectinload(Meeting.organizer),
            )
        )

        return result.scalar_one()
    
    
@router.post(
    "/{meeting_id}/confirm-held",
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
        409: {
            "description": "Conflict",
            "model": ErrorResponse,
        },
    },
)
async def confirm_held_meeting(
    meeting_id: int,
    payload: MeetingConfirmHeldRequest,
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
        .where(Meeting.id == meeting_id)
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
            detail="Meeting not found",
        )


    participant = next(
        (
            p
            for p in meeting.participants
            if p.employee_id == current_user.employee_id
        ),
        None,
    )


    if not participant:
        raise HTTPException(
            status_code=403,
            detail="Only participants can confirm meeting",
        )


    if participant.held_confirmed:
        raise HTTPException(
            status_code=409,
            detail="Meeting already confirmed",
        )


    participant.held_confirmed = payload.held
    participant.all_required_participants_present = (
        payload.all_required_participants_present
    )


    await db.commit()


    result = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting.id)
        .options(
            selectinload(Meeting.participants)
            .selectinload(MeetingParticipant.employee),
            selectinload(Meeting.organizer),
        )
    )

    return result.scalar_one()
