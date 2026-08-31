from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.current_user import AuthenticatedUser
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models import Meeting, MeetingParticipant
from app.models.employee import Employee
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.onboarding import Onboarding, OnboardingStatus
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    EmployeeDecisionRequest,
    EmployeeDecisionResponse,
    ManagerDecisionRequest,
    OnboardingOut,
)
from app.services.notification import notify_employee
from app.services.onboarding import OnboardingService

router = APIRouter(prefix="/employees")


@router.post(
    "/{employee_id}/onboarding/employee-decision",
    response_model=EmployeeDecisionResponse,
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
            "EMPLOYEE"
        ],
        "x-scope-rules": [
            "Only the Employee themself."
        ],
    },
)
async def submit_employee_decision(
    employee_id: int,
    payload: EmployeeDecisionRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles("EMPLOYEE")
    ),
    db: AsyncSession = Depends(get_db),
):

    if current_user.employee_id != employee_id:
        raise HTTPException(
            status_code=403,
            detail="Only employee can submit decision"
        )


    result = await db.execute(
        select(Onboarding)
        .where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = result.scalar_one_or_none()


    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found"
        )


    service = OnboardingService(db)


    try:
        onboarding = await service.submit_employee_decision(
            onboarding.id,
            payload.decision,
            payload.exit_type,
        )

        await db.commit()

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )


    return EmployeeDecisionResponse(
        employeeDecision=onboarding.employee_decision,
        managerDecision=onboarding.manager_decision,
        finalResult=onboarding.final_result,
    )
    
    
@router.post(
    "/{employee_id}/onboarding/manager-decision",
    response_model=EmployeeDecisionResponse,
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
            "MANAGER",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "Only authorized Direct Manager."
        ],
    },
)
async def submit_manager_decision(
    employee_id: int,
    payload: ManagerDecisionRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "MANAGER",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):

    employee_result = await db.execute(
        select(Employee)
        .where(
            Employee.id == employee_id
        )
    )

    employee = employee_result.scalar_one_or_none()


    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )


    if "MANAGER" in current_user.roles:

        if employee.manager_id != current_user.employee_id:
            raise HTTPException(
                status_code=403,
                detail="Only direct manager can submit decision"
            )


    onboarding_result = await db.execute(
        select(Onboarding)
        .where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = onboarding_result.scalar_one_or_none()


    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found"
        )


    service = OnboardingService(db)


    try:
        onboarding = await service.submit_manager_decision(
            onboarding.id,
            payload.decision,
            payload.exit_type,
        )

        await db.commit()


    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )


    return EmployeeDecisionResponse(
        employeeDecision=onboarding.employee_decision,
        managerDecision=onboarding.manager_decision,
        finalResult=onboarding.final_result,
    )
    
    
@router.post(
    "/{employee_id}/onboarding/notify-manager-after-hrbp",
    response_model=OnboardingOut,
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
            "HRBP",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "HRBP can perform this only for employees in assigned teams.",
        ],
    },
)
async def notify_manager_after_hrbp(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = result.scalar_one_or_none()


    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )


    if onboarding.current_phase_number >= 2:
        raise HTTPException(
            status_code=409,
            detail="Manager already notified",
        )


    result = await db.execute(
        select(Meeting)
        .where(
            Meeting.onboarding_id == onboarding.id,
            Meeting.onboarding_month == 1,
        )
    )

    meeting = result.scalar_one_or_none()


    if meeting is None:
        raise HTTPException(
            status_code=409,
            detail="Month 1 HRBP meeting not found",
        )


    result = await db.execute(
        select(MeetingParticipant)
        .where(
            MeetingParticipant.meeting_id == meeting.id
        )
    )

    participants = result.scalars().all()


    if not participants or not all(
        p.held_confirmed
        for p in participants
    ):
        raise HTTPException(
            status_code=409,
            detail="Meeting is not confirmed by all participants",
        )


    if not meeting.notes:
        raise HTTPException(
            status_code=409,
            detail="Meeting notes are required",
        )


    onboarding.current_phase_number = 2

    onboarding.status = OnboardingStatus.IN_PROGRESS

    await notify_employee(
        db,
        employee_id=employee_id,
        type="ONBOARDING_PHASE_ADVANCED",
        message="Your onboarding has moved to month 2. Your manager will schedule a meeting to set your tasks.",
        reference_type="ONBOARDING",
        reference_id=onboarding.id,
    )

    await db.commit()


    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(
            Onboarding.id == onboarding.id
        )
    )

    return result.scalar_one()
@router.post(
    "/{employee_id}/onboarding/check-month2-tasks-deadline",
    response_model=OnboardingOut,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": ["HRBP", "HR_MANAGER"],
        "x-usage": [
            "Intended to be invoked once per day (e.g. by an external cron) at end of business day.",
            "If the employee is in onboarding month 2, their month-2 meeting was held, "
            "and the manager still has not entered any tasks for that phase, "
            "the assigned HRBP is notified so they can fill the tasks in themselves.",
        ],
    },
)
async def check_month2_tasks_deadline(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles("HRBP", "HR_MANAGER")
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Onboarding).where(Onboarding.employee_id == employee_id)
    )
    onboarding = result.scalar_one_or_none()

    if onboarding is None:
        raise HTTPException(status_code=404, detail="Onboarding not found")

    if onboarding.current_phase_number != 2:
        raise HTTPException(
            status_code=409,
            detail="Employee is not in onboarding month 2",
        )

    meeting_result = await db.execute(
        select(Meeting).where(
            Meeting.onboarding_id == onboarding.id,
            Meeting.onboarding_month == 2,
        )
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=409,
            detail="Month 2 manager meeting has not been held yet",
        )

    participants_result = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting.id
        )
    )
    participants = participants_result.scalars().all()

    if not participants or not all(p.held_confirmed for p in participants):
        raise HTTPException(
            status_code=409,
            detail="Month 2 manager meeting has not been held yet",
        )

    phase_result = await db.execute(
        select(OnboardingPhase).where(
            OnboardingPhase.onboarding_id == onboarding.id,
            OnboardingPhase.phase_number == 2,
        )
    )
    phase = phase_result.scalar_one_or_none()

    task_count = 0
    if phase is not None:
        task_result = await db.execute(
            select(OnboardingTask).where(OnboardingTask.phase_id == phase.id)
        )
        task_count = len(task_result.scalars().all())

    if task_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Manager has already entered tasks for this phase",
        )

    employee_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = employee_result.scalar_one()

    hrbp_result = await db.execute(
        select(HrbpTeamAssignment.hrbp_id).where(
            HrbpTeamAssignment.team_id == employee.team_id
        )
    )
    hrbp_ids = hrbp_result.scalars().all()

    for hrbp_id in hrbp_ids:
        await notify_employee(
            db,
            employee_id=hrbp_id,
            type="MANAGER_TASKS_MISSING",
            message=(
                f"Manager has not entered month-2 onboarding tasks for "
                f"employee #{employee_id}. Please fill them in."
            ),
            reference_type="ONBOARDING",
            reference_id=onboarding.id,
        )

    await db.commit()

    result = await db.execute(
        select(Onboarding)
        .options(
            selectinload(Onboarding.buddy),
            selectinload(Onboarding.development_plan),
        )
        .where(Onboarding.id == onboarding.id)
    )

    return result.scalar_one()