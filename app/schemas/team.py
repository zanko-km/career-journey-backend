from pydantic import BaseModel

class TeamCreate(BaseModel):
    name: str

class TeamOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}