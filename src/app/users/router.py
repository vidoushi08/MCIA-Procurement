from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.database import get_db
from src.app.security import hash_password, require_roles
from src.app.users import models, schemas

router = APIRouter(prefix="/users", tags=["Users & Roles"])

@router.post("/", response_model=schemas.UserResponse)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_roles("ADMIN")),
):
    role = user.role.upper()
    if role not in schemas.ROLES:
        raise HTTPException(status_code=400, detail="Role must be STAFF, DEPT_HEAD or ADMIN")
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        department=user.department,
        role=role,
        password_hash=hash_password(user.password) if user.password else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[schemas.UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_roles("ADMIN")),
):
    return db.query(models.User).all()

