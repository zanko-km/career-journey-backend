import enum
from datetime import date

from pydantic import BaseModel, Field

from app.models.employee import EmployeeStatus
from app.models.onboarding import FinalResult, InvestmentDecision, OnboardingStatus


class OnboardingActionStatus(str, enum.Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    
    
class DepartmentOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {
        "from_attributes": True,
    }


class EmployeeSummary(BaseModel):
    id: int

    full_name: str = Field(
        alias="fullName"
    )

    nickname: str | None

    job_title: str | None = Field(
        default=None,
        alias="jobTitle",
    )

    status: EmployeeStatus

    career_stage: str = Field(
        alias="careerStage"
    )

    onboarding_phase: int | None = Field(
        default=None,
        alias="onboardingPhase"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

class OnboardingActionOut(BaseModel):
    id: int

    phase_id: int | None = Field(
        default=None,
        alias="phaseId",
    )

    title: str

    description: str | None = None

    due_date: date | None = Field(
        default=None,
        alias="dueDate",
    )

    status: OnboardingActionStatus

    created_by: EmployeeSummary | None = Field(
        default=None,
        alias="createdBy",
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

class TeamOut(BaseModel):
    id: int
    name: str
    department: DepartmentOut | None
    team_manager: EmployeeSummary | None = Field(
        default=None,
        alias="teamManager",
    )
    hrbps: list[EmployeeSummary] = Field(
        default_factory=list
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class PositionOut(BaseModel):
    id: int
    title: str
    job_description: str | None = Field(
        default=None,
        alias="jobDescription",
    )
    default_onboarding_duration_months: int | None = Field(
        default=None,
        alias="defaultOnboardingDurationMonths",
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

class OnboardingOut(BaseModel):
    id: int
    start_date: date = Field(alias="startDate")
    end_date: date | None = Field(
        default=None,
        alias="endDate",
    )
    duration_months: int = Field(alias="durationMonths")
    current_phase_number: int | None = Field(
        default=None,
        alias="currentPhaseNumber",
    )
    status: OnboardingStatus
    final_result: FinalResult = Field(
        alias="finalResult"
    )
    investment_decision: InvestmentDecision = Field(
        alias="investmentDecision"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class EmployeeCreate(BaseModel):
    username: str
    full_name: str = Field(alias="fullName")
    nickname: str | None = None

    join_date: date = Field(alias="joinDate")
    monthly_salary: float | None = Field(
        default=None,
        alias="monthlySalary",
    )

    team_id: int = Field(alias="teamId")
    position_id: int = Field(alias="positionId")
    direct_manager_id: int | None = Field(
        default=None,
        alias="directManagerId",
    )
    buddy_id: int | None = Field(
        default=None,
        alias="buddyId",
    )

    onboarding_start_date: date = Field(
        alias="onboardingStartDate"
    )
    onboarding_duration_months: int = Field(
        alias="onboardingDurationMonths"
    )

    initial_password: str = Field(
        alias="initialPassword"
    )

    model_config = {
        "populate_by_name": True,
    }

class EmployeeDetailOut(BaseModel):
    id: int
    username: str

    full_name: str = Field(alias="fullName")
    nickname: str | None

    join_date: date = Field(alias="joinDate")

    monthly_salary: float | None = Field(
        default=None,
        alias="monthlySalary",
    )

    position: PositionOut | None = None
    team: TeamOut | None = None

    buddy: EmployeeSummary | None = None

    hr_manager: EmployeeSummary | None = Field(
        default=None,
        alias="hrManager",
    )

    hrbp: EmployeeSummary | None = None

    direct_manager: EmployeeSummary | None = Field(
        default=None,
        alias="directManager",
    )

    team_manager: EmployeeSummary | None = Field(
        default=None,
        alias="teamManager",
    )

    onboarding: OnboardingOut | None = None

    next_actions: list[OnboardingActionOut] = Field(
        default_factory=list,
        alias="nextActions",
    )

    status: EmployeeStatus
    roles: list[str]

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
    
    
class EmployeeStatusUpdate(BaseModel):
    status: EmployeeStatus


class EmployeeRoleAssignRequest(BaseModel):
    role: str = Field(
        description="One of MANAGER, HRBP, HR_MANAGER. "
        "The base EMPLOYEE role is implicit and cannot be assigned/removed."
    )


class EmployeeRolesOut(BaseModel):
    employee_id: int = Field(alias="employeeId")
    roles: list[str]

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }