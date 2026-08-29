from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from sqlalchemy.orm import selectinload
from app.models.onboarding import Onboarding, OnboardingStatus
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingOut, StartOnboardingRequest,
    UpdateOnboardingRequest, OnboardingPhaseOut, OnboardingPhaseCreate,
    PhaseStatus, OnboardingActionOut, OnboardingActionCreate,
    OnboardingFeedbackOut, OnboardingFeedbackCreate,
    EmployeeDecisionRequest, EmployeeDecisionResponse, ManagerDecisionRequest,
)
from app.models.onboarding_feedback import OnboardingFeedback
from app.core.scope import require_employee_scope
from app.services.notification import notify_employee


router = APIRouter(prefix="/employees")


@router.get(
    "/{employee_id}/onboarding/feedback",
    response_model=list[OnboardingFeedbackOut],
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
        ],
    },
)
async def get_employee_onboarding_feedback(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):

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
            detail="Onboarding not found",
        )


    result = await db.execute(
        select(OnboardingFeedback)
        .where(
            OnboardingFeedback.employee_id == employee_id
        )
    )

    feedbacks = result.scalars().all()


    response = []


    for feedback in feedbacks:

        result = await db.execute(
            select(Employee)
            .where(
                Employee.id == feedback.created_by
            )
        )

        creator = result.scalar_one()


        response.append(
            OnboardingFeedbackOut(
                id=feedback.id,
                employeeId=feedback.employee_id,
                phaseId=feedback.phase_id,
                meetingId=feedback.meeting_id,
                feedback=feedback.feedback,
                createdAt=feedback.created_at,
                createdBy=creator,
            )
        )


    return response
@router.post(
    "/{employee_id}/onboarding/feedback",
    response_model=OnboardingFeedbackOut,
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
        422: {
            "description": "Validation Error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def create_employee_onboarding_feedback(
    employee_id: int,
    payload: OnboardingFeedbackCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )


    result = await db.execute(
        select(Onboarding).where(
            Onboarding.employee_id == employee_id
        )
    )

    onboarding = result.scalar_one_or_none()

    if onboarding is None:
        raise HTTPException(
            status_code=404,
            detail="Onboarding not found",
        )


    result = await db.execute(
        select(Employee).where(
            Employee.id == current_user.employee_id
        )
    )

    creator = result.scalar_one_or_none()

    if creator is None:
        raise HTTPException(
            status_code=404,
            detail="Creator employee not found",
        )


    feedback = OnboardingFeedback(
        employee_id=employee_id,
        phase_id=payload.phase_id,
        meeting_id=payload.meeting_id,
        feedback=payload.feedback,
        created_by=creator,
    )


    db.add(feedback)

    await db.flush()

    # Notify the employee's direct manager that month-1 HRBP feedback has
    # been written, so they can review it ahead of the month-2 hand-off.
    if employee.manager_id is not None:
        await notify_employee(
            db,
            employee_id=employee.manager_id,
            type="ONBOARDING_FEEDBACK_ADDED",
            message=(
                f"HRBP feedback has been added for employee #{employee_id} "
                "from their month-1 onboarding meeting."
            ),
            reference_type="ONBOARDING_FEEDBACK",
            reference_id=feedback.id,
        )

    await db.commit()

    await db.refresh(feedback)


    result = await db.execute(
        select(OnboardingFeedback)
        .options(
            selectinload(
                OnboardingFeedback.created_by
            )
        )
        .where(
            OnboardingFeedback.id == feedback.id
        )
    )

    return result.scalar_one()