from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.competency_cycle import CompetencyCyclePhase, CompetencyCycleStatus


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

    reviewStartedBy: int | None = Field(
        default=None,
        validation_alias="review_started_by_id",
    )
    
class StartReviewRequest(BaseModel):
    competencyIds: list[int]
    focusEndsAt: datetime | None = Field(
        default=None,
        alias="focusEndsAt",
    )
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    meetingScheduledAt: datetime = Field(
        alias="meetingScheduledAt",
        description=(
            "Required. A performance-review meeting is created "
            "automatically with the employee and their direct manager as "
            "participants (both are notified)."
=======
    meetingScheduledAt: datetime | None = Field(
        default=None,
        alias="meetingScheduledAt",
        description=(
            "Optional. If provided, a performance-review meeting is "
            "created automatically with the employee and their direct "
            "manager as participants (both are notified). If omitted, "
            "only the start-review notifications are sent and the HRBP "
            "can schedule the meeting separately via POST /meetings."
>>>>>>> af78ad1 (feat: adding notif feedback for manager, fixing the exit type, fixing the meeting bugs in competencies cycle)
=======
    meetingScheduledAt: datetime = Field(
        alias="meetingScheduledAt",
        description=(
            "Required. A performance-review meeting is created "
            "automatically with the employee and their direct manager as "
            "participants (both are notified)."
>>>>>>> bad410e (adding state machine tests and fixing actions for HRBP and employee)
=======
    meetingScheduledAt: datetime = Field(
        alias="meetingScheduledAt",
        description=(
            "Required. A performance-review meeting is created "
            "automatically with the employee and their direct manager as "
            "participants (both are notified)."
>>>>>>> bad410e (adding state machine tests and fixing actions for HRBP and employee)
        ),
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