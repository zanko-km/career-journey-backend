from pydantic import BaseModel, ConfigDict, Field

from app.models.meeting import (
    MeetingStatus,
)
from app.models.meeting_participant import MeetingResponseStatus
from datetime import datetime


class MeetingRespondRequest(BaseModel):
    response: MeetingResponseStatus

class EmployeeSummary(BaseModel):
    id: int
    full_name: str
    nickname: str | None = None
    job_title: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


class MeetingParticipantResponse(BaseModel):
    employee_id: int = Field(
        serialization_alias="employeeId"
    )

    employee: EmployeeSummary

    response_status: MeetingResponseStatus = Field(
        serialization_alias="response"
    )

    held_confirmed: bool = Field(
        serialization_alias="confirmedHeld"
    )
    all_required_participants_present: bool = Field(
        serialization_alias="allRequiredParticipantsPresent"
    )
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

class MeetingResponse(BaseModel):
    id: int

    organizer_id: int = Field(alias="organizerId")

    employee_id: int | None = Field(
        default=None,
        alias="employeeId"
    )

    scheduled_at: datetime = Field(alias="scheduledAt")

    status: MeetingStatus

    notes: str | None = None

    participants: list[MeetingParticipantResponse]

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
    
class MeetingCreate(BaseModel):
    employee_id: int = Field(
        alias="employeeId"
    )

    scheduled_at: datetime = Field(
        alias="scheduledAt"
    )

    participant_ids: list[int] = Field(
        alias="participantIds"
    )

    notes: str | None = None

    onboarding_id: int | None = Field(
        default=None,
        alias="onboardingId"
    )

    onboarding_month: int | None = Field(
        default=None,
        alias="onboardingMonth"
    )

    model_config = {
        "populate_by_name": True
    }
    
class MeetingConfirmHeldRequest(BaseModel):
    held: bool
    all_required_participants_present: bool = Field(
        alias="allRequiredParticipantsPresent"
    )

    model_config = {
        "populate_by_name": True
    }