from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeDetailOut, EmployeeSummary, EmployeeStatusUpdate, EmployeeCreate
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.models.team import Team
from app.models.onboarding import Onboarding
from app.schemas.errors import ErrorResponse
from app.schemas.onboarding import (
    OnboardingOut, StartOnboardingRequest,
    UpdateOnboardingRequest, OnboardingPhaseOut, OnboardingPhaseCreate,
    PhaseStatus, OnboardingActionOut, OnboardingActionCreate,
    OnboardingFeedbackOut, OnboardingFeedbackCreate,
    EmployeeDecisionRequest,EmployeeDecisionResponse, ManagerDecisionRequest)
from datetime import timedelta
from app.models.onboarding import OnboardingStatus
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.models.onboarding_feedback import OnboardingFeedback
from app.services.onboarding import OnboardingService
from app.models import Meeting, MeetingParticipant


router = APIRouter(prefix="/employees", tags=["Employees"])




@router.get(
    "",
    response_model=list[EmployeeSummary],
    responses={
        401: {
            "description": "Unauthorized",
            "model" : ErrorResponse
        },
        403: {
            "description": "Forbidden",
            "model" : ErrorResponse
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "Manager: management scope. HRBP: assigned teams. HR Manager: HR scope.",
        ],
    },
)
async def get_employees(
    current_user: AuthenticatedUser = Depends(
        require_roles("MANAGER", "HRBP", "HR_MANAGER")
    ),
    db: AsyncSession = Depends(get_db),
):
    options = selectinload(Employee.position)

    if "MANAGER" in current_user.roles:
        result = await db.execute(
            select(Employee)
            .options(options)
            .where(
                Employee.manager_id == current_user.employee_id
            )
        )
        return result.scalars().all()

    if "HRBP" in current_user.roles:
        result = await db.execute(
            select(Employee)
            .options(options)
            .join(
                HrbpTeamAssignment,
                Employee.team_id == HrbpTeamAssignment.team_id,
            )
            .where(
                HrbpTeamAssignment.hrbp_id == current_user.employee_id
            )
        )
        return result.scalars().all()

    if "HR_MANAGER" in current_user.roles:
        result = await db.execute(
            select(Employee)
            .options(options)
        )
        return result.scalars().all()

    return []

@router.get(
    "/{employee_id}",
    response_model=EmployeeDetailOut,
    responses={
        401: {
            "description": "Unauthorized",
            "model" : ErrorResponse
        },
        403: {
            "description": "Forbidden",
            "model" : ErrorResponse
        },
        404: {
            "description": "Conflict",
            "model" : ErrorResponse
        },
        422: {
            "description": "Validation Error",
            "model" : ErrorResponse
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
async def get_employee(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles("MANAGER", "HRBP", "HR_MANAGER")
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.position),

            selectinload(Employee.team).selectinload(
                Team.department
            ),

            selectinload(Employee.team).selectinload(
                Team.team_manager
            ),

            selectinload(Employee.team).selectinload(
                Team.hrbps
            ),

            selectinload(Employee.manager),

            selectinload(Employee.onboarding).selectinload(
                Onboarding.buddy
            ),

            selectinload(Employee.roles),
        )
        .where(
            Employee.id == employee_id
        )
    )

    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if "MANAGER" in current_user.roles:
        if employee.manager_id != current_user.employee_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

    if "HRBP" in current_user.roles:
        result = await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == current_user.employee_id,
                HrbpTeamAssignment.team_id == employee.team_id,
            )
        )

        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

    roles = [
        role.role
        for role in employee.roles
    ]

    hrbp = None

    if employee.team:
        result = await db.execute(
            select(Employee)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.hrbp_id == Employee.id,
            )
            .where(
                HrbpTeamAssignment.team_id == employee.team_id
            )
        )

        hrbp = result.scalar_one_or_none()
    return EmployeeDetailOut(
        id=employee.id,
        username=employee.username,
        fullName=employee.full_name,
        nickname=employee.nickname,
        joinDate=employee.join_date,
        monthlySalary=employee.monthly_salary,

        position=employee.position,
        team=employee.team,

        buddy=(
            employee.onboarding.buddy
            if employee.onboarding
            else None
        ),

        hrManager=None,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=[],

        status=employee.status,
        roles=roles,
    )

@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeDetailOut,
    responses={
        401: {
            "description": "Unauthorized",
            "model" : ErrorResponse
        },
        403: {
            "description": "Forbidden",
            "model" : ErrorResponse
        },
        404: {
            "description": "Conflict",
            "model" : ErrorResponse
        },
        409: {
            "description": "Conflict",
            "model" : ErrorResponse
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def update_employee_status(
    employee_id: int,
    payload: EmployeeStatusUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles("HRBP", "HR_MANAGER")
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.position),

            selectinload(Employee.team).selectinload(
                Team.department
            ),

            selectinload(Employee.team).selectinload(
                Team.team_manager
            ),

            selectinload(Employee.team).selectinload(
                Team.hrbps
            ),

            selectinload(Employee.manager),

            selectinload(Employee.onboarding).selectinload(
                Onboarding.buddy
            ),

            selectinload(Employee.roles),
        )
        .where(Employee.id == employee_id)
    )

    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    employee.status = payload.status

    await db.commit()

    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.position),

            selectinload(Employee.team).selectinload(
                Team.department
            ),

            selectinload(Employee.team).selectinload(
                Team.team_manager
            ),

            selectinload(Employee.team).selectinload(
                Team.hrbps
            ),

            selectinload(Employee.manager),

            selectinload(Employee.onboarding).selectinload(
                Onboarding.buddy
            ),

            selectinload(Employee.roles),
        )
        .where(Employee.id == employee_id)
    )

    employee = result.scalar_one()

    roles = [
        role.role
        for role in employee.roles
    ]

    hrbp = None

    if employee.team:
        result = await db.execute(
            select(Employee)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.hrbp_id == Employee.id,
            )
            .where(
                HrbpTeamAssignment.team_id == employee.team_id
            )
        )

        hrbp = result.scalar_one_or_none()

    return EmployeeDetailOut(
        id=employee.id,
        username=employee.username,
        fullName=employee.full_name,
        nickname=employee.nickname,
        joinDate=employee.join_date,
        monthlySalary=employee.monthly_salary,

        position=employee.position,
        team=employee.team,

        buddy=(
            employee.onboarding.buddy
            if employee.onboarding
            else None
        ),

        hrManager=None,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=[],

        status=employee.status,
        roles=roles,
    )
    
    
@router.post(
    "",
    response_model=EmployeeDetailOut,
    status_code=201,
    responses={
        401: {
            "description": "Unauthorized",
            "model" : ErrorResponse
        },
        403: {
            "description": "Forbidden",
            "model" : ErrorResponse
        },
        409: {
            "description": "Conflict",
            "model" : ErrorResponse
        },
        422: {
            "description": "Validation Error",
            "model" : ErrorResponse
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "HRBP can create only inside assigned teams.",
        ],
        "x-business-rules": [
            "username must be globally unique.",
        ],
    },
)
async def create_employee(
    payload: EmployeeCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles("HRBP", "HR_MANAGER")
    ),
    db: AsyncSession = Depends(get_db),
):
    if "HRBP" in current_user.roles:
        result = await db.execute(
            select(HrbpTeamAssignment).where(
                HrbpTeamAssignment.hrbp_id == current_user.employee_id,
                HrbpTeamAssignment.team_id == payload.team_id,
            )
        )

        assignment = result.scalar_one_or_none()

        if assignment is None:
            raise HTTPException(
                status_code=403,
                detail="Forbidden",
            )

    employee = Employee(
        username=payload.username,
        full_name=payload.full_name,
        nickname=payload.nickname,
        join_date=payload.join_date,
        monthly_salary=payload.monthly_salary,
        team_id=payload.team_id,
        position_id=payload.position_id,
        manager_id=payload.direct_manager_id,
    )

    db.add(employee)

    try:
        async with db.begin_nested():
            await db.flush()
    except IntegrityError as exc:
        if "employees_username_key" in str(exc.orig):
            raise HTTPException(
                status_code=409,
                detail="Username already exists",
            )

        raise

    onboarding = Onboarding(
        employee_id=employee.id,
        buddy_id=payload.buddy_id,
        start_date=payload.onboarding_start_date,
        end_date=None,
        duration_months=payload.onboarding_duration_months,
        current_phase_number=1,
    )

    db.add(onboarding)

    await db.commit()

    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.position),

            selectinload(Employee.team).selectinload(
                Team.department
            ),

            selectinload(Employee.team).selectinload(
                Team.team_manager
            ),

            selectinload(Employee.team).selectinload(
                Team.hrbps
            ),

            selectinload(Employee.manager),

            selectinload(Employee.onboarding).selectinload(
                Onboarding.buddy
            ),

            selectinload(Employee.roles),
        )
        .where(Employee.id == employee.id)
    )

    employee = result.scalar_one()

    roles = [
        role.role
        for role in employee.roles
    ]

    hrbp = None

    if employee.team:
        result = await db.execute(
            select(Employee)
            .join(
                HrbpTeamAssignment,
                HrbpTeamAssignment.hrbp_id == Employee.id,
            )
            .where(
                HrbpTeamAssignment.team_id == employee.team_id
            )
        )

        hrbp = result.scalar_one_or_none()

    return EmployeeDetailOut(
        id=employee.id,
        username=employee.username,
        fullName=employee.full_name,
        nickname=employee.nickname,
        joinDate=employee.join_date,
        monthlySalary=employee.monthly_salary,

        position=employee.position,
        team=employee.team,

        buddy=(
            employee.onboarding.buddy
            if employee.onboarding
            else None
        ),

        hrManager=None,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=[],

        status=employee.status,
        roles=roles,
    )
    
    
@router.get(
    "/{employee_id}/onboarding",
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
    },
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def get_employee_onboarding(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "MANAGER",
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

    return onboarding


@router.post(
    "/{employee_id}/onboarding",
    response_model=OnboardingOut,
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
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def start_employee_onboarding(
    employee_id: int,
    payload: StartOnboardingRequest,
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

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Onboarding already exists",
        )


    end_date = (
        payload.start_date +
        timedelta(
            days=30 * payload.duration_months
        )
    )


    onboarding = Onboarding(
        employee_id=employee_id,
        start_date=payload.start_date,
        end_date=end_date,
        duration_months=payload.duration_months,
        buddy_id=payload.buddy_id,
        current_phase_number=1,
    )


    db.add(onboarding)

    await db.commit()

    await db.refresh(onboarding)


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


@router.patch(
    "/{employee_id}/onboarding",
    response_model=OnboardingOut,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def update_employee_onboarding(
    employee_id: int,
    payload: UpdateOnboardingRequest,
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


    if onboarding.status != OnboardingStatus.NOT_STARTED:
        raise HTTPException(
            status_code=409,
            detail="Cannot update started onboarding",
        )


    if payload.start_date:
        onboarding.start_date = payload.start_date

    if payload.duration_months:
        onboarding.duration_months = payload.duration_months

    if payload.buddy_id:
        onboarding.buddy_id = payload.buddy_id


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

    onboarding = result.scalar_one()

    return onboarding


@router.get(
    "/{employee_id}/onboarding/phases",
    response_model=list[OnboardingPhaseOut],
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
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def get_employee_onboarding_phases(
    employee_id: int,
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
        select(OnboardingPhase)
        .where(
            OnboardingPhase.onboarding_id == onboarding.id
        )
        .order_by(
            OnboardingPhase.phase_number
        )
    )

    phases = result.scalars().all()

    return phases


@router.post(
    "/{employee_id}/onboarding/phases",
    response_model=OnboardingPhaseOut,
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
async def create_employee_onboarding_phase(
    employee_id: int,
    payload: OnboardingPhaseCreate,
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


    existing = await db.execute(
        select(OnboardingPhase)
        .where(
            OnboardingPhase.onboarding_id == onboarding.id,
            OnboardingPhase.phase_number == payload.phase_number,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Phase number already exists",
        )


    phase = OnboardingPhase(
        onboarding_id=onboarding.id,
        phase_number=payload.phase_number,
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=PhaseStatus.PENDING,
    )

    db.add(phase)

    await db.commit()
    await db.refresh(phase)

    return phase


@router.get(
    "/{employee_id}/onboarding/actions",
    response_model=list[OnboardingActionOut],
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
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def get_employee_onboarding_actions(
    employee_id: int,
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
        select(OnboardingTask)
        .join(
            OnboardingPhase,
            OnboardingTask.phase_id == OnboardingPhase.id,
        )
        .where(
            OnboardingPhase.onboarding_id == onboarding.id
        )
    )

    tasks = result.scalars().all()


    response = []


    for task in tasks:

        result = await db.execute(
            select(Employee)
            .where(
                Employee.id == task.assigned_by
            )
        )

        creator = result.scalar_one()


        response.append(
            OnboardingActionOut(
                id=task.id,
                phaseId=task.phase_id,
                title=task.title,
                description=getattr(
                    task,
                    "description",
                    None
                ),
                dueDate=task.due_date,
                status=task.status,
                createdBy=creator,
            )
        )


    return response


@router.post(
    "/{employee_id}/onboarding/actions",
    response_model=OnboardingActionOut,
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
async def create_employee_onboarding_action(
    employee_id: int,
    payload: OnboardingActionCreate,
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
        select(OnboardingPhase)
        .where(
            OnboardingPhase.id == payload.phase_id,
            OnboardingPhase.onboarding_id == onboarding.id,
        )
    )

    phase = result.scalar_one_or_none()


    if phase is None:
        raise HTTPException(
            status_code=404,
            detail="Phase not found",
        )


    task = OnboardingTask(
        phase_id=payload.phase_id,
        assigned_by=current_user.employee_id,
        assigned_to=employee_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        status=payload.status,
    )


    db.add(task)

    await db.commit()
    await db.refresh(task)


    result = await db.execute(
        select(Employee)
        .where(
            Employee.id == task.assigned_by
        )
    )

    creator = result.scalar_one()


    return OnboardingActionOut(
        id=task.id,
        phaseId=task.phase_id,
        title=task.title,
        description=task.description,
        dueDate=task.due_date,
        status=task.status,
        createdBy=creator,
    )
    
    
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
            payload.decision
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
            payload.decision
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
