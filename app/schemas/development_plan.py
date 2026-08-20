from pydantic import BaseModel, ConfigDict
from app.models.user import EmployeeRoleType

class DevelopmentPlanUpsertItem(BaseModel):
    competencyId: int
    comment: str | None = None
    task: str | None = None
    completed: bool = False


class DevelopmentPlanUpsertRequest(BaseModel):
    items: list[DevelopmentPlanUpsertItem]


class DevelopmentPlanItem(BaseModel):
    id: int
    competencyId: int
    comment: str | None
    task: str | None
    authorRole: str
    authorId: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class DevelopmentPlanResponse(BaseModel):
    employeeItems: list[DevelopmentPlanItem]
    hrbpItems: list[DevelopmentPlanItem]
    
class DevelopmentPlanItemResponse(BaseModel):
    id: int
    competencyId: int
    authorId: int
    authorRole: EmployeeRoleType
    completed: bool
    comment: str | None = None
    task: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )