from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
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
from app.models.meeting_participant import MeetingResponseStatus
from app.models import Employee
from app.models.user import EmployeeRoleType
from app.services.notification import notify_employee
router = APIRouter(prefix="/meetings", tags=["Employees"])


async def _can_organize_downward(
    db: AsyncSession,
    current_user: AuthenticatedUser,
    employee: Employee,
) -> bool:
    """Existing behaviour: a Manager/HRBP/HR Manager organizing a meeting
    *about* someone they manage/support (organizer sits above the subject)."""

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
    """The set of people `employee` is allowed to request a meeting with:
    their direct manager, their team manager (one layer up), any HRBP
    assigned to their team, and any HR Manager. This is what lets an
    Employee meet their Manager/TeamManager/HRBP/HR Manager, a Manager
    meet their own manager, and an HRBP meet the HR Manager."""

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

    # Case A: organizer sits above the subject in the org chart
    # (Manager/HRBP/HR Manager organizing a meeting about someone they
    # manage or support). This is the pre-existing "downward" flow.
    allowed = await _can_organize_downward(db, current_user, employee)

    # Case B: organizer is requesting a meeting about themself with
    # someone above them (direct manager, team manager, assigned HRBP,
    # or HR Manager). Covers Employee -> Manager/TeamManager/HRBP/HRManager,
    # Manager -> own manager, and HRBP -> HR Manager.
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