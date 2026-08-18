from pydantic import BaseModel, SecretStr
from app.models.user import EmployeeRoleType

class LoginRequest(BaseModel):
    username: str
    password: SecretStr


class UserSummary(BaseModel):
    id: int
    employeeId: int
    username: str
    fullName: str
    roles: list[EmployeeRoleType]


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int | None = None
    user: UserSummary
    
class RefreshRequest(BaseModel):
    refreshToken: str