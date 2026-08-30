from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee, EmployeeStatus
from app.schemas.employee import (
    EmployeeDetailOut, EmployeeSummary, EmployeeStatusUpdate, EmployeeCreate,
    EmployeeRoleAssignRequest, EmployeeRolesOut,
)
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.employee_role import EmployeeRole
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.models.team import Team
from app.models.onboarding import Onboarding, OnboardingStatus, FinalResult
from app.schemas.errors import ErrorResponse
from app.models.onboarding_phase import OnboardingPhase
from app.models.onboarding_task import OnboardingTask
from app.core.scope import require_employee_scope
from app.core.supabase import get_supabase_admin
from app.models.user import User
from supabase import Client


router = APIRouter(prefix="/employees")


async def get_hr_manager_employee(db: AsyncSession) -> Employee | None:

    result = await db.execute(
        select(Employee)
        .join(EmployeeRole, EmployeeRole.employee_id == Employee.id)
        .where(EmployeeRole.role == "HR_MANAGER")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_next_actions(db: AsyncSession, employee: Employee) -> list[OnboardingTask]:

    if employee.onboarding is None or employee.onboarding.current_phase_number is None:
        return []

    phase_result = await db.execute(
        select(OnboardingPhase).where(
            OnboardingPhase.onboarding_id == employee.onboarding.id,
            OnboardingPhase.phase_number == employee.onboarding.current_phase_number,
        )
    )
    phase = phase_result.scalar_one_or_none()

    if phase is None:
        return []

    tasks_result = await db.execute(
        select(OnboardingTask)
        .options(selectinload(OnboardingTask.assigned_by_employee))
        .where(
            OnboardingTask.phase_id == phase.id,
            OnboardingTask.assigned_to == employee.id,
        )
        .order_by(OnboardingTask.id)
    )
    return list(tasks_result.scalars().all())
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
        "x-business-rules": [
            "This is how the HRBP records the continue/exit decision made "
            "at the end of onboarding (or at any other time).",
            "If the employee has an open Onboarding (IN_PROGRESS or "
            "FINAL_DECISION_PENDING), it is kept in sync: setting status "
            "to EXITED also finalizes the onboarding as EXITED; setting "
            "status back to ACTIVE while FINAL_DECISION_PENDING finalizes "
            "it as COMPLETED.",
        ],
    },
)
async def update_employee_status(
    employee_id: int,
    payload: EmployeeStatusUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles("HRBP", "HR_MANAGER")
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
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

    if payload.status == EmployeeStatus.EXITED:
        if payload.exit_type is None:
            raise HTTPException(
                status_code=422,
                detail="exitType (RESIGNATION or TERMINATION) is required when status is EXITED",
            )

        employee.exit_type = payload.exit_type
    else:
        # exit_type is only meaningful alongside EXITED; clear it if the
        # employee is moved to any other status.
        employee.exit_type = None

    employee.status = payload.status

    # Per the requirement doc, this is how the HRBP records the
    # continue/exit decision made in the end-of-onboarding meeting. Keep
    # the Onboarding record's status/final_result in sync so it doesn't
    # silently drift from Employee.status (e.g. staying
    # FINAL_DECISION_PENDING forever after the employee has already been
    # marked EXITED here). This only touches an onboarding that is still
    # open (not already COMPLETED/EXITED/CANCELLED); it never overrides a
    # decision that's already been finalized through the
    # employee-decision/manager-decision flow.
    if employee.onboarding is not None and employee.onboarding.status in (
        OnboardingStatus.IN_PROGRESS,
        OnboardingStatus.FINAL_DECISION_PENDING,
    ):
        if payload.status == EmployeeStatus.EXITED:
            employee.onboarding.status = OnboardingStatus.EXITED
            employee.onboarding.final_result = FinalResult.EXIT
        elif (
            payload.status == EmployeeStatus.ACTIVE
            and employee.onboarding.status
            == OnboardingStatus.FINAL_DECISION_PENDING
        ):
            employee.onboarding.status = OnboardingStatus.COMPLETED
            employee.onboarding.final_result = FinalResult.CONTINUE

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

    hr_manager = await get_hr_manager_employee(db)
    next_actions = await get_next_actions(db, employee)

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

        hrManager=hr_manager,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=next_actions,

        status=employee.status,
        exitType=employee.exit_type,
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
    supabase_admin: Client = Depends(get_supabase_admin),
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

    await db.flush()

    try:
        auth_response = supabase_admin.auth.admin.create_user(
            {
                "email": payload.username,
                "password": payload.initial_password,
                "email_confirm": True,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to provision authentication account: {exc}",
        )

    if auth_response.user is None:
        raise HTTPException(
            status_code=502,
            detail="Failed to provision authentication account",
        )

    user = User(
        auth_provider_id=str(auth_response.user.id),
        employee_id=employee.id,
    )

    db.add(user)

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

    hr_manager = await get_hr_manager_employee(db)
    next_actions = await get_next_actions(db, employee)

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

        hrManager=hr_manager,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=next_actions,

        status=employee.status,
        exitType=employee.exit_type,
        roles=roles,
    )
    
    
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
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
    },
)
async def get_employee(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles("EMPLOYEE", "MANAGER", "HRBP", "HR_MANAGER")
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

    if employee_id != current_user.employee_id and "HR_MANAGER" not in current_user.roles:
        is_direct_manager = (
            "MANAGER" in current_user.roles
            and employee.manager_id == current_user.employee_id
        )

        is_assigned_hrbp = False
        if "HRBP" in current_user.roles:
            hrbp_result = await db.execute(
                select(HrbpTeamAssignment).where(
                    HrbpTeamAssignment.hrbp_id == current_user.employee_id,
                    HrbpTeamAssignment.team_id == employee.team_id,
                )
            )
            is_assigned_hrbp = hrbp_result.scalar_one_or_none() is not None

        if not is_direct_manager and not is_assigned_hrbp:
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
    hr_manager = await get_hr_manager_employee(db)
    next_actions = await get_next_actions(db, employee)

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

        hrManager=hr_manager,
        hrbp=hrbp,

        directManager=employee.manager,

        teamManager=(
            employee.team.team_manager
            if employee.team
            else None
        ),

        onboarding=employee.onboarding,

        nextActions=next_actions,

        status=employee.status,
        exitType=employee.exit_type,
        roles=roles,
    )