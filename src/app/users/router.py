from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.database import get_db
from src.app.users import models, schemas

router = APIRouter(prefix="/users", tags=["Users & Roles"])

@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        department=user.department,
        role=user.role.upper()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()
