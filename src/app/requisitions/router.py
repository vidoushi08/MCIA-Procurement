import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.app import notifications
from src.app.database import get_db
from src.app.inventory import models as inventory_models
from src.app.requisitions import models, schemas
from src.app.security import get_current_user, require_roles
from src.app.tenders import models as tender_models
from src.app.users import models as user_models

router = APIRouter(prefix="/requisitions", tags=["Requisitions & 3-Tier Signatures"])
logger = logging.getLogger("mcia.requisitions")


def log_action(db: Session, req_id: int, action: str, details: str = None):
    db.add(models.RequisitionAuditLog(requisition_id=req_id, action=action, details=details))


def _request_items(db: Session, req: models.Requisition, create_legacy: bool = False):
    rows = db.query(models.RequisitionItem).filter(
        models.RequisitionItem.requisition_id == req.id
    ).order_by(models.RequisitionItem.id).all()
    if rows or not create_legacy:
        return rows
    row = models.RequisitionItem(
        requisition_id=req.id,
        item_id=req.item_id,
        quantity_requested=req.quantity_requested,
        status=req.status,
    )
    db.add(row)
    db.flush()
    return [row]


def _item_summary(db: Session, req: models.Requisition) -> str:
    summary = []
    for line in _request_items(db, req):
        item = db.query(inventory_models.InventoryItem).filter(
            inventory_models.InventoryItem.id == line.item_id
        ).first()
        item_name = item.item_name if item else f"Item #{line.item_id}"
        summary.append(f"{item_name} × {line.quantity_requested}")
    return "; ".join(summary)


def _send_staff_email(db: Session, req: models.Requisition, subject: str, body: str):
    staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
    if staff is None:
        logger.error("Cannot notify missing staff user %s for requisition %s", req.staff_id, req.id)
        return
    notifications.send_email(staff.email, subject, body)


def _send_admin_email(db: Session, subject: str, body: str):
    admins = db.query(user_models.User).filter(user_models.User.role == "ADMIN").all()
    if not admins:
        logger.error("No Administrator recipients configured for %s", subject)
    for admin in admins:
        notifications.send_email(admin.email, subject, body)


@router.post("/", response_model=schemas.RequisitionResponse)
def submit_requisition(
    req: schemas.RequisitionCreate,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(require_roles("STAFF")),
):
    if req.staff_id != current.id:
        raise HTTPException(status_code=403, detail="Staff can only submit requisitions for themselves")

    requested_items = req.items
    if not requested_items and req.item_id is not None and req.quantity_requested is not None:
        requested_items = [
            schemas.RequisitionItemCreate(item_id=req.item_id, quantity_requested=req.quantity_requested)
        ]
    if not requested_items:
        raise HTTPException(status_code=422, detail="At least one requested item is required")
    item_ids = [line.item_id for line in requested_items]
    if len(item_ids) != len(set(item_ids)):
        raise HTTPException(status_code=400, detail="Each item can appear only once in a request")

    inventory = db.query(inventory_models.InventoryItem).filter(
        inventory_models.InventoryItem.id.in_(item_ids)
    ).all()
    inventory_by_id = {item.id: item for item in inventory}
    if len(inventory_by_id) != len(item_ids):
        raise HTTPException(status_code=404, detail="One or more stationery items were not found")
    for line in requested_items:
        item = inventory_by_id[line.item_id]
        if current.department.strip().lower() != item.department_category.strip().lower():
            raise HTTPException(status_code=400, detail=f"{item.item_name} is not available to your department")

    first = requested_items[0]
    new_req = models.Requisition(
        staff_id=current.id,
        item_id=first.item_id,
        quantity_requested=first.quantity_requested,
        staff_signed=True,
        staff_signed_at=datetime.datetime.utcnow(),
        status="PENDING_HEAD",
    )
    db.add(new_req)
    db.flush()
    for line in requested_items:
        db.add(models.RequisitionItem(
            requisition_id=new_req.id,
            item_id=line.item_id,
            quantity_requested=line.quantity_requested,
            status="PENDING_HEAD",
        ))
    details = "; ".join(
        f"{line.quantity_requested} x {inventory_by_id[line.item_id].item_name}"
        for line in requested_items
    )
    log_action(db, new_req.id, "SUBMITTED", f"Staff {current.id} requested {details}"[:255])
    db.commit()
    db.refresh(new_req)
    ref = f"REQ-{new_req.id:04d}"
    body = (
        f"New requisition {ref} from {current.full_name} ({current.department}): "
        f"{_item_summary(db, new_req)}. Please sign in to review."
    )
    heads = db.query(user_models.User).filter(user_models.User.role == "DEPT_HEAD").all()
    matching_heads = [
        head for head in heads
        if head.department.strip().casefold() == current.department.strip().casefold()
    ]
    if not matching_heads:
        logger.error(
            "No Department Head recipients configured for department %s",
            current.department,
        )
    for department_head in matching_heads:
        notifications.send_email(
            department_head.email,
            f"New requisition {ref} awaiting Head review",
            body,
        )
    return enrich(db, [new_req])[0]


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

    requested_items = _request_items(db, req, create_legacy=True)
    needs_quotes = False
    for line in requested_items:
        item = db.query(inventory_models.InventoryItem).filter(
            inventory_models.InventoryItem.id == line.item_id
        ).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Stationery item {line.item_id} not found")
        if item.quantity_in_stock < line.quantity_requested:
            line.status = "PENDING_QUOTES"
            needs_quotes = True
        else:
            line.status = "PENDING_ADMIN"

    req.head_signed = True
    req.head_signed_at = datetime.datetime.utcnow()
    req.status = "PENDING_QUOTES" if needs_quotes else "PENDING_ADMIN"
    log_action(db, req.id, "HEAD_SIGNED")
    db.commit()
    db.refresh(req)
    ref = f"REQ-{req.id:04d}"
    _send_staff_email(
        db,
        req,
        f"Requisition {ref} approved by Department Head",
        f"Your requisition {ref} was approved by the Department Head. "
        f"Status: {req.status}. Items: {_item_summary(db, req)}.",
    )
    return enrich(db, [req])[0]


@router.put("/{req_id}/submit-quotes", response_model=schemas.RequisitionResponse)
def submit_quotes_to_admin(
    req_id: int,
    db: Session = Depends(get_db),
    current: user_models.User = Depends(require_roles("STAFF")),
):
    req = db.query(models.Requisition).filter(models.Requisition.id == req_id).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.staff_id != current.id:
        raise HTTPException(status_code=403, detail="Staff can only submit quotations for their own request")
    if req.status != "PENDING_QUOTES":
        raise HTTPException(status_code=400, detail="This request is not waiting for staff quotations")

    pending_lines = [
        line for line in _request_items(db, req, create_legacy=True)
        if line.status == "PENDING_QUOTES"
    ]
    missing = []
    for line in pending_lines:
        count = db.query(tender_models.SupplierQuotationLine).filter(
            tender_models.SupplierQuotationLine.requisition_item_id == line.id
        ).count()
        if count == 0:
            item = db.query(inventory_models.InventoryItem).filter(
                inventory_models.InventoryItem.id == line.item_id
            ).first()
            missing.append(item.item_name if item else f"Item #{line.item_id}")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Add at least one supplier quotation for each out-of-stock line: " + ", ".join(missing),
        )

    req.status = "PENDING_ADMIN"
    req.comparison_generated_at = None
    for line in _request_items(db, req):
        if line.status == "PENDING_QUOTES":
            line.status = "PENDING_ADMIN"
    log_action(db, req.id, "QUOTES_SUBMITTED_TO_ADMIN")
    db.commit()
    db.refresh(req)
    staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
    staff_name = staff.full_name if staff else f"Staff #{req.staff_id}"
    department = staff.department if staff else "Unknown department"
    ref = f"REQ-{req.id:04d}"
    body = (
        f"{staff_name} ({department}) submitted supplier quotations for {ref}. "
        f"Items: {_item_summary(db, req)}. Please review the comparative table."
    )
    _send_admin_email(db, f"Quotes submitted for {ref}", body)
    return enrich(db, [req])[0]


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
    elif req.status != "PENDING_ADMIN":
        raise HTTPException(status_code=400, detail=f"Requisition is {req.status}, not awaiting Administrator approval")

    req.status = "DECLINED"
    req.declined_at = datetime.datetime.utcnow()
    req.declined_by_role = role
    req.decline_reason = body.reason.strip()
    for line in _request_items(db, req, create_legacy=True):
        line.status = "DECLINED"
    log_action(db, req.id, "DECLINED", f"{role}: {req.decline_reason}")
    db.commit()
    db.refresh(req)
    ref = f"REQ-{req.id:04d}"
    role_label = "Department Head" if role == "DEPT_HEAD" else "Administrator"
    _send_staff_email(
        db,
        req,
        f"Requisition {ref} declined by {role_label}",
        f"Your requisition {ref} was declined by {role_label}. "
        f"Reason: {req.decline_reason}",
    )
    return enrich(db, [req])[0]


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

    requested_items = _request_items(db, req, create_legacy=True)
    stock_by_line = {}
    missing_quotes = []
    for line in requested_items:
        item = db.query(inventory_models.InventoryItem).filter(
            inventory_models.InventoryItem.id == line.item_id
        ).with_for_update().first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Stationery item {line.item_id} not found")
        stock_by_line[line.id] = item
        if item.quantity_in_stock < line.quantity_requested:
            has_quote = db.query(tender_models.SupplierQuotationLine.id).filter(
                tender_models.SupplierQuotationLine.requisition_item_id == line.id
            ).first()
            if not has_quote:
                missing_quotes.append(line)

    if missing_quotes:
        for line in missing_quotes:
            line.status = "PENDING_QUOTES"
        req.status = "PENDING_QUOTES"
        db.commit()
        db.refresh(req)
        return enrich(db, [req])[0]

    has_quotations = any(
        db.query(tender_models.SupplierQuotationLine.id).filter(
            tender_models.SupplierQuotationLine.requisition_item_id == line.id
        ).first()
        for line in requested_items
    )
    if has_quotations and not req.comparison_generated_at:
        raise HTTPException(
            status_code=400,
            detail="Generate the comparative table before Administrator approval",
        )

    req.head_signed = True
    req.admin_signed = True
    req.admin_signed_at = datetime.datetime.utcnow()
    has_tender = False
    for line in requested_items:
        item = stock_by_line[line.id]
        if item.quantity_in_stock >= line.quantity_requested:
            item.quantity_in_stock -= line.quantity_requested
            line.status = "FULFILLED_FROM_STOCK"
            log_action(db, req.id, "STOCK_DEDUCTED", f"{line.quantity_requested} x {item.item_name}")
        else:
            line.status = "TENDER_OPEN"
            has_tender = True
            log_action(db, req.id, "TENDER_OPENED", f"Insufficient stock for {item.item_name}")
    req.status = "TENDER_OPEN" if has_tender else "FULFILLED_FROM_STOCK"
    log_action(db, req.id, "ADMIN_SIGNED")
    db.commit()
    db.refresh(req)
    ref = f"REQ-{req.id:04d}"
    _send_staff_email(
        db,
        req,
        f"Requisition {ref} approved by Administrator",
        f"Your requisition {ref} was approved by the Administrator. "
        f"Status: {req.status}. Items: {_item_summary(db, req)}.",
    )
    return enrich(db, [req])[0]


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
    staff_by_id = {u.id: u for u in db.query(user_models.User).all()}
    item_by_id = {i.id: i for i in db.query(inventory_models.InventoryItem).all()}
    rows = []
    for req in reqs:
        data = schemas.RequisitionResponse.model_validate(req).model_dump()
        staff = staff_by_id.get(req.staff_id)
        request_items = _request_items(db, req)
        if request_items:
            data["items"] = []
            for line in request_items:
                item = item_by_id.get(line.item_id)
                quotation_count = db.query(tender_models.SupplierQuotationLine.id).filter(
                    tender_models.SupplierQuotationLine.requisition_item_id == line.id
                ).count()
                data["items"].append({
                    "id": line.id,
                    "item_id": line.item_id,
                    "quantity_requested": line.quantity_requested,
                    "status": line.status,
                    "item_name": item.item_name if item else None,
                    "department_category": item.department_category if item else None,
                    "quotation_count": quotation_count,
                })
        else:
            item = item_by_id.get(req.item_id)
            data["items"] = [{
                "id": None,
                "item_id": req.item_id,
                "quantity_requested": req.quantity_requested,
                "status": req.status,
                "item_name": item.item_name if item else None,
                "department_category": item.department_category if item else None,
            }]
        first = data["items"][0]
        data["item_name"] = first["item_name"]
        data["staff_name"] = staff.full_name if staff else None
        data["department"] = staff.department if staff else None
        data["head_approval_status"] = (
            "Declined" if req.declined_by_role == "DEPT_HEAD"
            else "Approved" if req.head_signed
            else "Pending"
        )
        data["admin_approval_status"] = (
            "Declined" if req.declined_by_role == "ADMIN"
            else "Approved" if req.admin_signed
            else "Pending"
        )
        rows.append(data)
    return rows
