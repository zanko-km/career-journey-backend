from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from app.models.user import EmployeeRoleType
from app.schemas.employee import (
    EmployeeDetailOut, EmployeeSummary, EmployeeStatusUpdate, EmployeeCreate,
    EmployeeRoleAssignRequest, EmployeeRolesOut,
)
from app.models.hrbp_team_assignment import HrbpTeamAssignment
from app.models.employee_role import EmployeeRole
from app.schemas.errors import ErrorResponse
from app.core.scope import require_employee_scope


router = APIRouter(prefix="/employees")


ASSIGNABLE_ROLES = {
    EmployeeRoleType.MANAGER.value,
    EmployeeRoleType.HRBP.value,
    EmployeeRoleType.HR_MANAGER.value,
}
@router.get(
    "/{employee_id}/roles",
    response_model=EmployeeRolesOut,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": ["EMPLOYEE", "MANAGER", "HRBP", "HR_MANAGER"],
        "x-scope-rules": ["Self, direct manager, assigned HRBP, or HR Manager."],
    },
)
async def list_employee_roles(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles("EMPLOYEE", "MANAGER", "HRBP", "HR_MANAGER")
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):
    employee = await db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = await db.execute(
        select(EmployeeRole.role).where(EmployeeRole.employee_id == employee_id)
    )

    roles = [EmployeeRoleType.EMPLOYEE.value] + list(result.scalars().all())

    return EmployeeRolesOut(employeeId=employee_id, roles=roles)
@router.post(
    "/{employee_id}/roles",
    response_model=EmployeeRolesOut,
    status_code=201,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
        422: {"description": "Validation Error", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": ["HR_MANAGER"],
        "x-business-rules": [
            "Only HR Manager can grant organizational roles (MANAGER, HRBP, HR_MANAGER).",
            "The base EMPLOYEE role is implicit for every employee and cannot be assigned.",
        ],
    },
)
async def assign_employee_role(
    employee_id: int,
    payload: EmployeeRoleAssignRequest,
    current_user: AuthenticatedUser = Depends(require_roles("HR_MANAGER")),
    db: AsyncSession = Depends(get_db),
):
    role = payload.role.strip().upper()

    if role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(ASSIGNABLE_ROLES)}",
        )

    employee = await db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing_result = await db.execute(
        select(EmployeeRole).where(
            EmployeeRole.employee_id == employee_id,
            EmployeeRole.role == role,
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Employee already has role {role}",
        )

    db.add(EmployeeRole(employee_id=employee_id, role=role))

    await db.commit()

    result = await db.execute(
        select(EmployeeRole.role).where(EmployeeRole.employee_id == employee_id)
    )

    roles = [EmployeeRoleType.EMPLOYEE.value] + list(result.scalars().all())

    return EmployeeRolesOut(employeeId=employee_id, roles=roles)
@router.delete(
    "/{employee_id}/roles/{role}",
    response_model=EmployeeRolesOut,
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Conflict", "model": ErrorResponse},
    },
    openapi_extra={
        "x-allowed-roles": ["HR_MANAGER"],
        "x-business-rules": [
            "Cannot remove MANAGER while the employee still has direct reports.",
            "Cannot remove HRBP while the employee still has assigned teams.",
        ],
    },
)
async def remove_employee_role(
    employee_id: int,
    role: str,
    current_user: AuthenticatedUser = Depends(require_roles("HR_MANAGER")),
    db: AsyncSession = Depends(get_db),
):
    role = role.strip().upper()

    employee = await db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = await db.execute(
        select(EmployeeRole).where(
            EmployeeRole.employee_id == employee_id,
            EmployeeRole.role == role,
        )
    )

    role_row = result.scalar_one_or_none()

    if role_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee does not have role {role}",
        )

    if role == EmployeeRoleType.MANAGER.value:
        reports_result = await db.execute(
            select(Employee.id).where(Employee.manager_id == employee_id)
        )
        if reports_result.first() is not None:
            raise HTTPException(
                status_code=409,
                detail="Cannot remove MANAGER role while employee still has direct reports",
            )

    if role == EmployeeRoleType.HRBP.value:
        assignments_result = await db.execute(
            select(HrbpTeamAssignment.id).where(
                HrbpTeamAssignment.hrbp_id == employee_id
            )
        )
        if assignments_result.first() is not None:
            raise HTTPException(
                status_code=409,
                detail="Cannot remove HRBP role while employee still has assigned teams",
            )

    await db.delete(role_row)
    await db.commit()

    result = await db.execute(
        select(EmployeeRole.role).where(EmployeeRole.employee_id == employee_id)
    )

    roles = [EmployeeRoleType.EMPLOYEE.value] + list(result.scalars().all())

    return EmployeeRolesOut(employeeId=employee_id, roles=roles)
