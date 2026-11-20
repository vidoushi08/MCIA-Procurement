from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import datetime

from src.app.database import get_db
from src.app.requisitions import models, schemas
from src.app.security import get_current_user, require_roles
from src.app.users import models as user_models
from src.app.inventory import models as inventory_models

router = APIRouter(prefix="/requisitions", tags=["Requisitions & 3-Tier Signatures"])

def log_action(db: Session, req_id: int, action: str, details: str = None):
    db.add(models.RequisitionAuditLog(requisition_id=req_id, action=action, details=details))

@router.post("/", response_model=schemas.RequisitionResponse)
def submit_requisition(
    req: schemas.RequisitionCreate,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(require_roles("STAFF")),
):
    if req.staff_id != current.id:
        raise HTTPException(status_code=403, detail="Staff can only submit requisitions for themselves")
    staff = current

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
        staff_signed_at=datetime.datetime.utcnow(),
        status="PENDING_HEAD"
    )
    db.add(new_req)
    db.flush()
    log_action(db, new_req.id, "SUBMITTED", f"Staff {req.staff_id} requested {req.quantity_requested} x {item.item_name}")
    db.commit()
    db.refresh(new_req)
    return new_req

@router.put("/{req_id}/sign-head", response_model=schemas.RequisitionResponse)
def department_head_sign(
    req_id: int,
    db: Session = Depends(get_db),
    head: user_models.User = Depends(require_roles("DEPT_HEAD")),
):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
    if staff is None or staff.department.strip().lower() != head.department.strip().lower():
        raise HTTPException(status_code=403, detail="Department Head can only sign requests from their own department")
    if req.status != "PENDING_HEAD":
        raise HTTPException(status_code=400, detail=f"Requisition is {req.status}, not awaiting Department Head approval")

    req.head_signed = True
    req.head_signed_at = datetime.datetime.utcnow()
    req.status = "PENDING_ADMIN"
    log_action(db, req.id, "HEAD_SIGNED")
    db.commit()
    db.refresh(req)
    return req

@router.put("/{req_id}/decline", response_model=schemas.RequisitionResponse)
def decline_requisition(
    req_id: int,
    body: schemas.DeclineRequest,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(require_roles("DEPT_HEAD", "ADMIN")),
):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")

    role = current.role.upper()
    if role == "DEPT_HEAD":
        staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
        if staff is None or staff.department.strip().lower() != current.department.strip().lower():
            raise HTTPException(status_code=403, detail="Department Head can only decline requests from their own department")
        if req.status != "PENDING_HEAD":
            raise HTTPException(status_code=400, detail=f"Requisition is {req.status}, not awaiting Department Head approval")
    else:
        if req.status != "PENDING_ADMIN":
            raise HTTPException(status_code=400, detail=f"Requisition is {req.status}, not awaiting Administrator approval")

    req.status = "DECLINED"
    req.declined_at = datetime.datetime.utcnow()
    req.decline_reason = body.reason.strip()
    log_action(db, req.id, "DECLINED", f"{role}: {req.decline_reason}")
    db.commit()
    db.refresh(req)
    return req

@router.put("/{req_id}/sign-admin", response_model=schemas.RequisitionResponse)
def admin_sign_and_check_stock(
    req_id: int,
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.status != "PENDING_ADMIN":
        raise HTTPException(status_code=400, detail=f"Requisition is {req.status}, not awaiting Administrator approval")
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
def get_live_progress_tracker(
    staff_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(get_current_user),
):
    if current.role.upper() == "STAFF" and current.id != staff_id:
        raise HTTPException(status_code=403, detail="Staff can only view their own requisitions")
    reqs = db.query(models.Requisition).filter(models.Requisition.staff_id == staff_id).all()
    return enrich(db, reqs)

@router.get("/", response_model=List[schemas.RequisitionResponse])
def get_all_requisitions(
    db: Session = Depends(get_db),
    current: user_models.User = Depends(require_roles("DEPT_HEAD", "ADMIN")),
):
    query = db.query(models.Requisition)
    if current.role.upper() == "DEPT_HEAD":
        staff_ids = [u.id for u in db.query(user_models.User).all()
                     if u.department.strip().lower() == current.department.strip().lower()]
        query = query.filter(models.Requisition.staff_id.in_(staff_ids))
    return enrich(db, query.order_by(models.Requisition.id.desc()).all())


def enrich(db: Session, reqs: List[models.Requisition]) -> List[dict]:
    """Attach staff name, department and item name so queue screens can show them."""
    staff_by_id = {u.id: u for u in db.query(user_models.User).all()}
    item_by_id = {i.id: i for i in db.query(inventory_models.InventoryItem).all()}
    rows = []
    for r in reqs:
        data = schemas.RequisitionResponse.model_validate(r).model_dump()
        staff = staff_by_id.get(r.staff_id)
        item = item_by_id.get(r.item_id)
        data["staff_name"] = staff.full_name if staff else None
        data["department"] = staff.department if staff else None
        data["item_name"] = item.item_name if item else None
        rows.append(data)
    return rows

