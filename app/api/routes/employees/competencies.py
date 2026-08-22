from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.current_user import AuthenticatedUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_roles
from app.core.database import get_db
from app.models.employee import Employee
from sqlalchemy.orm import selectinload
from app.schemas.errors import ErrorResponse
from app.models import Meeting, MeetingParticipant, Competency, EmployeeCompetency, CompetencyCycle, MeetingStatus
from app.schemas.competency import CompetencyResponse, AssignEmployeeCompetenciesRequest
from app.schemas.competency_cycle import CompetencyCycleResponse, CompetencyCycleCreateRequest
from app.models.competency_cycle import CompetencyCycleStatus, CompetencyCyclePhase
from app.core.scope import require_employee_scope


<<<<<<< HEAD
router = APIRouter(prefix="/employees")
=======
router = APIRouter(prefix="/employees", tags=["Employees"])
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)


@router.get(
    "/{employee_id}/competencies",
    response_model=list[CompetencyResponse],
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
async def list_employee_competencies(
    employee_id: int,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "EMPLOYEE",
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):

    employee = await db.get(
        Employee,
        employee_id,
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )


    result = await db.execute(
        select(Competency)
        .join(
            EmployeeCompetency,
            EmployeeCompetency.competency_id == Competency.id,
        )
        .where(
            EmployeeCompetency.employee_id == employee_id
        )
        .where(
            Competency.active.is_(True)
        )
        .order_by(
            Competency.name
        )
    )

    return result.scalars().all()
@router.post(
    "/{employee_id}/competencies",
    response_model=list[CompetencyResponse],
    status_code=status.HTTP_200_OK,
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
<<<<<<< HEAD
    openapi_extra={
        "x-allowed-roles": [
            "MANAGER",
            "HRBP",
            "HR_MANAGER",
        ],
        "x-scope-rules": [
            "MANAGER may only assign competencies to employees in their "
            "own management hierarchy (direct or indirect reports).",
            "HRBP may only assign competencies to employees in their "
            "assigned teams.",
            "HR_MANAGER is unrestricted.",
        ],
    },
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
)
async def assign_employee_competencies(
    employee_id: int,
    payload: AssignEmployeeCompetenciesRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
<<<<<<< HEAD
            "MANAGER",
=======
>>>>>>> 7532306 (refactor: split employees.py (2528 lines) into a routes package)
            "HRBP",
            "HR_MANAGER",
        )
    ),
    _scope: AuthenticatedUser = Depends(require_employee_scope("employee_id")),
    db: AsyncSession = Depends(get_db),
):

    employee_result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = employee_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )


    competency_result = await db.execute(
        select(Competency).where(
            Competency.id.in_(payload.competencyIds)
        )
    )

    competencies = competency_result.scalars().all()


    if len(competencies) != len(
        payload.competencyIds
    ):
        raise HTTPException(
            status_code=404,
            detail="Competency not found",
        )


    existing_result = await db.execute(
        select(EmployeeCompetency).where(
            EmployeeCompetency.employee_id == employee_id,
            EmployeeCompetency.competency_id.in_(
                payload.competencyIds
            )
        )
    )

    existing = existing_result.scalars().all()


    if existing:
        raise HTTPException(
            status_code=409,
            detail="Competency already assigned",
        )


    assignments = [
        EmployeeCompetency(
            employee_id=employee_id,
            competency_id=competency.id,
        )
        for competency in competencies
    ]

    db.add_all(assignments)

    await db.commit()


    return competencies
@router.post(
    "/{employee_id}/competency-cycles",
    response_model=CompetencyCycleResponse,
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
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
    openapi_extra={
        "x-allowed-roles": [
            "HRBP",
            "HR_MANAGER",
        ],
        "x-business-rules": [
            "A newly created cycle starts in ACTIVE status.",
            "endDate is optional and must not be used as an automatic Competency Review trigger.",
            "Competency Review starts only through POST /competency-cycles/{cycleId}/start-review by an authorized HRBP or HR_MANAGER.",
        ],
    },
)
async def create_competency_cycle(
    employee_id: int,
    payload: CompetencyCycleCreateRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "HRBP",
            "HR_MANAGER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    employee_result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = employee_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    cycle = CompetencyCycle(
        employee_id=employee_id,
        start_date=payload.startDate,
        end_date=payload.endDate,
        status=CompetencyCycleStatus.ACTIVE,
        phase=CompetencyCyclePhase.RATING,
    )

    db.add(cycle)

    await db.commit()
    await db.refresh(cycle)

    return {
        "id": cycle.id,
        "employeeId": cycle.employee_id,
        "startDate": cycle.start_date,
        "endDate": cycle.end_date,
        "status": cycle.status,
        "phase": cycle.phase,
        "meetingNotes": cycle.meeting_notes,
        "meetingCompleted": cycle.meeting_completed,
        "focusEndsAt": cycle.focus_ends_at,
        "reviewStartedAt": cycle.review_started_at,
        "focusCompetencies": [],
        "reviewStartedBy": None,
    }
@router.get(
    "/{employee_id}/competency-cycles",
    response_model=list[CompetencyCycleResponse],
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
async def list_competency_cycles(
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

    employee_result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id
        )
    )

    employee = employee_result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )


    if (
        "EMPLOYEE" in current_user.roles
        and current_user.employee_id != employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )


    result = await db.execute(
        select(CompetencyCycle)
        .where(
            CompetencyCycle.employee_id == employee_id
        )
        .options(
            selectinload(
                CompetencyCycle.focus_competencies
            ),
            selectinload(
                CompetencyCycle.review_started_by
            ),
        )
        .order_by(
            CompetencyCycle.start_date.desc()
        )
    )


    return result.scalars().all()
