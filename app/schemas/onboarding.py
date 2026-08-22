from datetime import date
from pydantic import BaseModel, ConfigDict, Field

from app.models.onboarding import (
    OnboardingStatus,
    Decision,
    FinalResult,
    InvestmentDecision,
)
from app.models.onboarding_phase import PhaseStatus
from app.models.employee import ExitType
from datetime import datetime



class DevelopmentPlanOut(BaseModel):
    goals: str
    skills: str
    training: str
    mentoring: str
    next_steps: str = Field(
        alias="nextSteps"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class BuddyOut(BaseModel):
    id: int
    full_name: str
    nickname: str | None
    job_title: str | None

    model_config = ConfigDict(
        from_attributes=True
    )


class OnboardingOut(BaseModel):
    id: int

    employee_id: int = Field(
        alias="employeeId"
    )

    start_date: date = Field(
        alias="startDate"
    )

    end_date: date | None = Field(
        alias="endDate"
    )

    duration_months: int = Field(
        alias="durationMonths"
    )

    buddy: BuddyOut | None

    status: OnboardingStatus

    current_phase_number: int | None = Field(
        alias="currentPhaseNumber"
    )

    employee_decision: Decision | None = Field(
        alias="employeeDecision"
    )

    manager_decision: Decision | None = Field(
        alias="managerDecision"
    )

    final_result: FinalResult = Field(
        alias="finalResult"
    )

    investment_decision: InvestmentDecision = Field(
        alias="investmentDecision"
    )

    development_plan: DevelopmentPlanOut | None = Field(
        alias="developmentPlan"
    )


    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
    
    
class StartOnboardingRequest(BaseModel):
    start_date: date = Field(alias="startDate")
    duration_months: int = Field(alias="durationMonths")
    buddy_id: int | None = Field(
        default=None,
        alias="buddyId"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )
    
    
class UpdateOnboardingRequest(BaseModel):
    start_date: date | None = Field(
        default=None,
        alias="startDate"
    )

    duration_months: int | None = Field(
        default=None,
        alias="durationMonths"
    )

    buddy_id: int | None = Field(
        default=None,
        alias="buddyId"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )
    
class OnboardingPhaseOut(BaseModel):
    id: int

    phase_number: int = Field(
        alias="phaseNumber"
    )

    title: str

    start_date: date = Field(
        alias="startDate"
    )

    end_date: date = Field(
        alias="endDate"
    )

    status: PhaseStatus

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
    
    
class OnboardingPhaseCreate(BaseModel):
    phase_number: int = Field(
        alias="phaseNumber"
    )

    title: str

    start_date: date = Field(
        alias="startDate"
    )

    end_date: date = Field(
        alias="endDate"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )
    


class OnboardingActionCreate(BaseModel):
    phase_id: int | None = Field(
        default=None,
        alias="phaseId"
    )

    title: str

    description: str | None = None

    due_date: date | None = Field(
        default=None,
        alias="dueDate"
    )

    status: str = "PENDING"

    model_config = ConfigDict(
        populate_by_name=True
    )


class CreatedByOut(BaseModel):
    id: int
    full_name: str = Field(alias="fullName")
    nickname: str | None
    job_title: str | None = Field(alias="jobTitle")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class OnboardingActionOut(BaseModel):
    id: int

    phase_id: int | None = Field(
        alias="phaseId"
    )

    title: str

    description: str | None

    due_date: date | None = Field(
        alias="dueDate"
    )

    status: str

    created_by: CreatedByOut = Field(
        alias="createdBy"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
    
class OnboardingFeedbackCreate(BaseModel):
    phase_id: int | None = Field(
        default=None,
        alias="phaseId"
    )

    meeting_id: int | None = Field(
        default=None,
        alias="meetingId"
    )

    feedback: str

    model_config = ConfigDict(
        populate_by_name=True
    )

class EmployeeSummary(BaseModel):
    id: int
    full_name: str
    nickname: str | None
    job_title: str | None

    model_config = {
        "from_attributes": True
    }
    

class OnboardingFeedbackOut(BaseModel):
    id: int

    employee_id: int = Field(
        alias="employeeId"
    )

    phase_id: int | None = Field(
        alias="phaseId"
    )

    meeting_id: int | None = Field(
        alias="meetingId"
    )

    feedback: str

    created_by: EmployeeSummary = Field(
        alias="createdBy"
    )

    created_at: datetime = Field(
        alias="createdAt"
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class EmployeeDecisionRequest(BaseModel):
    decision: Decision
    exit_type: ExitType | None = Field(
        default=None,
        alias="exitType",
    )

    model_config = ConfigDict(populate_by_name=True)


class ManagerDecisionRequest(BaseModel):
    decision: Decision
    exit_type: ExitType | None = Field(
        default=None,
        alias="exitType",
    )

    model_config = ConfigDict(populate_by_name=True)

class EmployeeDecisionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    employeeDecision: Decision | None = Field(
        serialization_alias="employeeDecision"
    )

    managerDecision: Decision | None = Field(
        serialization_alias="managerDecision"
    )

    finalResult: FinalResult = Field(
        serialization_alias="finalResult"
    )