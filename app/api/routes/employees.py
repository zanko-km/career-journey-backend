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