from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from src.app.database import get_db
from src.app.requisitions import models, schemas
from src.app.users import models as user_models
from src.app.inventory import models as inventory_models

router = APIRouter(prefix="/requisitions", tags=["Requisitions & 3-Tier Signatures"])

def log_action(db: Session, req_id: int, action: str, details: str = None):
    db.add(models.RequisitionAuditLog(requisition_id=req_id, action=action, details=details))

@router.post("/", response_model=schemas.RequisitionResponse)
def submit_requisition(req: schemas.RequisitionCreate, db: Session = Depends(get_db)):
    staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff user not found")

    item = db.query(inventory_models.InventoryItem).filter(inventory_models.InventoryItem.id == req.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stationery item not found")

    if staff.department.strip().lower() != item.department_category.strip().lower():
        raise HTTPException(status_code=400, detail="Item does not belong to the staff member's department")

    new_req = models.Requisition(
        staff_id=req.staff_id,
        item_id=req.item_id,
        quantity_requested=req.quantity_requested,
        staff_signed=True,
        status="PENDING_HEAD"
    )
    db.add(new_req)
    db.flush()
    log_action(db, new_req.id, "SUBMITTED", f"Staff {req.staff_id} requested {req.quantity_requested} x {item.item_name}")
    db.commit()
    db.refresh(new_req)
    return new_req

@router.put("/{req_id}/sign-head", response_model=schemas.RequisitionResponse)
def department_head_sign(req_id: int, db: Session = Depends(get_db)):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.head_signed:
        raise HTTPException(status_code=400, detail="Department Head has already signed this request")

    req.head_signed = True
    req.head_signed_at = datetime.datetime.utcnow()
    req.status = "PENDING_ADMIN"
    log_action(db, req.id, "HEAD_SIGNED")
    db.commit()
    db.refresh(req)
    return req

@router.put("/{req_id}/sign-admin", response_model=schemas.RequisitionResponse)
def admin_sign_and_check_stock(req_id: int, db: Session = Depends(get_db)):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if not req.head_signed:
        raise HTTPException(status_code=400, detail="Department Head signature is required before Admin approval")
    if req.admin_signed:
        raise HTTPException(status_code=400, detail="Administrator has already signed this request")

    # Lock the stock row so concurrent approvals cannot both deduct the same stock
    item = db.query(inventory_models.InventoryItem).filter(
        inventory_models.InventoryItem.id == req.item_id
    ).with_for_update().first()
    if not item:
        raise HTTPException(status_code=404, detail="Stationery item not found")

    req.admin_signed = True
    req.admin_signed_at = datetime.datetime.utcnow()
    log_action(db, req.id, "ADMIN_SIGNED")

    # Automated Stock Check & Atomic Deduction
    if item.quantity_in_stock >= req.quantity_requested:
        item.quantity_in_stock -= req.quantity_requested
        req.status = "FULFILLED_FROM_STOCK"
        log_action(db, req.id, "STOCK_DEDUCTED", f"{req.quantity_requested} x {item.item_name}")
    else:
        req.status = "TENDER_OPEN"
        log_action(db, req.id, "TENDER_OPENED", f"Insufficient stock for {item.item_name}")

    db.commit()
    db.refresh(req)
    return req


@router.get("/staff/{staff_id}/progress", response_model=List[schemas.RequisitionResponse])
def get_live_progress_tracker(staff_id: int, db: Session = Depends(get_db)):
    return db.query(models.Requisition).filter(models.Requisition.staff_id == staff_id).all()

@router.get("/", response_model=List[schemas.RequisitionResponse])
def get_all_requisitions(db: Session = Depends(get_db)):
    return db.query(models.Requisition).all()
