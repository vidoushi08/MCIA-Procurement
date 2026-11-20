from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from src.app.database import get_db
from src.app.security import get_current_user, require_roles
from src.app.inventory import models, schemas
from src.app.users import models as user_models

router = APIRouter(prefix="/inventory", tags=["Stationery Inventory"])

@router.post("/", response_model=schemas.ItemResponse)
def add_stationery_item(
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    existing = db.query(models.InventoryItem).filter(models.InventoryItem.item_name == item.item_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stationery item already exists in catalog")
    
    new_item = models.InventoryItem(**item.model_dump())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/", response_model=List[schemas.ItemResponse])
def get_stationery_catalog(
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: user_models.User = Depends(get_current_user),
):
    query = db.query(models.InventoryItem)
    if department:
        query = query.filter(models.InventoryItem.department_category.ilike(f"%{department}%"))
    return query.all()
