from pydantic import BaseModel, Field
from app.models.employee import EmployeeStatus, CareerStage

class TeamCreate(BaseModel):
    name: str

    department_id: int = Field(
        alias="departmentId"
    )

    team_manager_id: int = Field(
        alias="teamManagerId"
    )

    model_config = {
        "populate_by_name": True
    }


class HrbpTeamAssignmentCreate(BaseModel):
    hrbp_id: int = Field(alias="hrbpId")
    team_id: int = Field(alias="teamId")

    model_config = {
        "populate_by_name": True
    }


class HrbpTeamAssignmentOut(BaseModel):
    id: int
    hrbp_id: int = Field(alias="hrbpId")
    team_id: int = Field(alias="teamId")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

class DepartmentOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {
        "from_attributes": True
    }



class EmployeeSummary(BaseModel):
    id: int

    full_name: str = Field(
        alias="fullName"
    )

    nickname: str | None

    job_title: str | None = Field(
        default=None,
        alias="jobTitle"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }

class TeamEmployeeOut(BaseModel):
    id: int

    full_name: str = Field(
        alias="fullName"
    )

    nickname: str | None

    job_title: str | None = Field(
        default=None,
        alias="jobTitle"
    )

    status: EmployeeStatus

    career_stage: CareerStage = Field(
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

class TeamOut(BaseModel):

    id: int
    name: str

    department: DepartmentOut

    team_manager: EmployeeSummary | None = Field(
        alias="teamManager"
    )

    hrbps: list[EmployeeSummary] = Field(default_factory=list)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }