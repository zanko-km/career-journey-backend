from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.competency import CompetencyResponse
from app.schemas.employee import EmployeeSummary
from app.models.competency_cycle import CompetencyCycleStatus, CompetencyCyclePhase


class SelfAssessmentScore(BaseModel):
    competencyId: int
    score: int = Field(ge=1, le=5)


class SelfAssessmentRequest(BaseModel):
    scores: list[SelfAssessmentScore]

class ManagerAssessmentScore(BaseModel):
    competencyId: int
    score: int = Field(ge=1, le=5)


class ManagerAssessmentRequest(BaseModel):
    scores: list[ManagerAssessmentScore]

class CompetencyRadarData(BaseModel):
    labels: list[str]
    employeeScores: list[float]
    managerScores: list[float]

    model_config = ConfigDict(
        populate_by_name=True
    )
    
    
class CompetencyCycleResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    employeeId: int = Field(validation_alias="employee_id")
    startDate: date = Field(validation_alias="start_date")
    endDate: date | None = Field(
        default=None,
        validation_alias="end_date",
    )
    status: CompetencyCycleStatus
    focusCompetencies: list = []
    phase: CompetencyCyclePhase

    meetingNotes: str | None = Field(
        default=None,
        validation_alias="meeting_notes",
    )

    meetingCompleted: bool = Field(
        validation_alias="meeting_completed",
    )

    focusEndsAt: datetime | None = Field(
        default=None,
        validation_alias="focus_ends_at",
    )

    reviewStartedAt: datetime | None = Field(
        default=None,
        validation_alias="review_started_at",
    )

    reviewStartedBy: object | None = Field(
        default=None,
        validation_alias="review_started_by",
    )
    
class StartReviewRequest(BaseModel):
    competencyIds: list[int]
    focusEndsAt: datetime | None = Field(
        default=None,
        alias="focusEndsAt",
    )

    model_config = {
        "populate_by_name": True
    }


class CompetencyCycleCreateRequest(BaseModel):
    startDate: date = Field(
        alias="startDate"
    )

    endDate: date | None = Field(
        default=None,
        alias="endDate"
    )

    model_config = {
        "populate_by_name": True
    }