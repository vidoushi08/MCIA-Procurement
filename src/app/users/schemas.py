from typing import Optional

from pydantic import BaseModel, EmailStr, Field

ROLES = ("STAFF", "DEPT_HEAD", "ADMIN")


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    department: str
    role: str  # "STAFF", "DEPT_HEAD", or "ADMIN"


class UserCreate(UserBase):
    password: Optional[str] = Field(default=None, min_length=8)


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
