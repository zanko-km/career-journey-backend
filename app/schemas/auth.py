from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserSummary(BaseModel):
    id: int
    employeeId: int
    username: str
    fullName: str
    roles: list


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int | None = None
    user: UserSummary
    
class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int | None = None