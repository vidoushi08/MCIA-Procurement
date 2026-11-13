from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    department: str
    role: str  # "STAFF", "DEPT_HEAD", or "ADMIN"

class UserResponse(UserCreate):
    id: int

    class Config:
        from_attributes = True
