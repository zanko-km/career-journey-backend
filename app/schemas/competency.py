from pydantic import BaseModel, ConfigDict, Field

class CompetencyCreate(BaseModel):
    name: str
    description: str | None = None
    

class CompetencyResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    active: bool

    model_config = ConfigDict(
        from_attributes=True
    )
    
class AssignEmployeeCompetenciesRequest(BaseModel):
    competencyIds: list[int] = Field(
        min_length=1
    )