from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app import audit, notifications
from src.app.database import get_db
from src.app.security import require_roles
from src.app.finance import models, schemas, scheduler
from src.app.inventory import models as inv_models
from src.app.tenders import models as tender_models
from src.app.requisitions import models as req_models
from src.app.users import models as user_models

router = APIRouter(prefix="/finance", tags=["Cheque Payments & SLA Delivery"])


def refresh_requisition_status(db: Session, req: req_models.Requisition):
    items = db.query(req_models.RequisitionItem).filter(
        req_models.RequisitionItem.requisition_id == req.id
    ).all()
    if not items:
        return
    statuses = {item.status for item in items}
    if "TENDER_OPEN" in statuses:
        req.status = "TENDER_OPEN"
    elif "PAID_AWAITING_DELIVERY" in statuses:
        req.status = "PAID_AWAITING_DELIVERY"
    elif statuses == {"FULFILLED_FROM_STOCK"}:
        req.status = "FULFILLED_FROM_STOCK"
    elif statuses.issubset({"FULFILLED_FROM_STOCK", "COMPLETED"}):
        req.status = "COMPLETED" if "COMPLETED" in statuses else "FULFILLED_FROM_STOCK"


@router.post("/approve-and-pay", response_model=schemas.PaymentResponse)
def approve_quote_and_log_cheque(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    admin: user_models.User = Depends(require_roles("ADMIN")),
):
    if bool(payment.quotation_id) == bool(payment.quotation_line_id):
        raise HTTPException(status_code=422, detail="Provide exactly one quotation or quotation line")

    quote_line = None
    if payment.quotation_line_id is not None:
        quote_line = db.query(tender_models.SupplierQuotationLine).filter(
            tender_models.SupplierQuotationLine.id == payment.quotation_line_id
        ).first()
        if not quote_line:
            raise HTTPException(status_code=404, detail="Supplier quotation line not found")
        quote = db.query(tender_models.SupplierQuotation).filter(
            tender_models.SupplierQuotation.id == quote_line.quotation_id
        ).first()
    else:
        quote = db.query(tender_models.SupplierQuotation).filter(
            tender_models.SupplierQuotation.id == payment.quotation_id
        ).first()
        if quote:
            candidate_lines = db.query(tender_models.SupplierQuotationLine).filter(
                tender_models.SupplierQuotationLine.quotation_id == quote.id
            ).all()
            if len(candidate_lines) == 1:
                quote_line = candidate_lines[0]
            elif candidate_lines:
                raise HTTPException(status_code=400, detail="Choose a quotation line for payment")
    if not quote:
        raise HTTPException(status_code=404, detail="Supplier quotation not found")

    req = db.query(req_models.Requisition).filter(
        req_models.Requisition.id == quote.requisition_id
    ).with_for_update().first()
    if req is None or req.status != "TENDER_OPEN":
        raise HTTPException(status_code=400, detail="Only requisitions open for tender can be paid")

    if db.query(models.PaymentAndDelivery).filter(
        models.PaymentAndDelivery.cheque_number == payment.cheque_number
    ).first():
        raise HTTPException(status_code=400, detail="Cheque number has already been used")

    if quote_line is not None:
        request_item = db.query(req_models.RequisitionItem).filter(
            req_models.RequisitionItem.id == quote_line.requisition_item_id
        ).with_for_update().first()
        if request_item is None or request_item.status != "TENDER_OPEN":
            raise HTTPException(status_code=400, detail="This request item is not open for tender")
        if db.query(models.PaymentAndDelivery).filter(
            models.PaymentAndDelivery.quotation_line_id == quote_line.id
        ).first():
            raise HTTPException(status_code=400, detail="This request item has already been paid")
        if quote_line.is_compliant is not True:
            raise HTTPException(status_code=400, detail="Only a quotation line marked compliant can be approved")
        compliant_lines = db.query(tender_models.SupplierQuotationLine).filter(
            tender_models.SupplierQuotationLine.requisition_item_id == request_item.id,
            tender_models.SupplierQuotationLine.is_compliant.is_(True),
        ).all()
        lowest_price = min(line.total_price for line in compliant_lines)
        if quote_line.total_price != lowest_price:
            raise HTTPException(status_code=400, detail="Only the lowest compliant quotation line can be approved")
        if abs(payment.amount_paid - quote_line.total_price) > 0.01:
            raise HTTPException(status_code=400, detail="Payment amount must match the approved quotation line")
        for line in compliant_lines:
            line.is_approved_lowest = (line.id == quote_line.id)
        request_item.status = "PAID_AWAITING_DELIVERY"
    else:
        already_paid = db.query(models.PaymentAndDelivery).join(
            tender_models.SupplierQuotation,
            models.PaymentAndDelivery.quotation_id == tender_models.SupplierQuotation.id,
        ).filter(tender_models.SupplierQuotation.requisition_id == req.id).first()
        if already_paid:
            raise HTTPException(status_code=400, detail="This requisition has already been paid")
        quotes = db.query(tender_models.SupplierQuotation).filter(
            tender_models.SupplierQuotation.requisition_id == req.id
        ).all()
        compliant = [q for q in quotes if q.is_compliant is True]
        if quote not in compliant:
            raise HTTPException(status_code=400, detail="Only a quotation marked compliant can be approved")
        lowest_price = min(q.total_price for q in compliant)
        if quote.total_price > lowest_price:
            raise HTTPException(status_code=400, detail="Only the lowest compliant quotation can be approved")
        for q in quotes:
            q.is_approved_lowest = (q.id == quote.id)

    new_payment = models.PaymentAndDelivery(
        quotation_id=quote.id,
        quotation_line_id=quote_line.id if quote_line else None,
        cheque_number=payment.cheque_number,
        amount_paid=payment.amount_paid
    )
    db.add(new_payment)
    db.flush()
    if quote_line is not None:
        refresh_requisition_status(db, req)
    else:
        req.status = "PAID_AWAITING_DELIVERY"
    audit.record(db, admin, "PAYMENT_APPROVED", "payment", new_payment.id,
                 f"Requisition {req.id}, quote {quote.id}, cheque {payment.cheque_number}, {payment.amount_paid}")
    db.commit()
    db.refresh(new_payment)
    ref = f"REQ-{req.id:04d}"
    item_description = (
        quote_line.quoted_item_description if quote_line else quote.quoted_item_description
    )
    notifications.send_email(
        quote.supplier_email,
        f"Payment recorded for requisition {ref}",
        f"Payment of MUR {new_payment.amount_paid:.2f} was recorded for "
        f"{item_description} under requisition {ref}. "
        f"Cheque number: {new_payment.cheque_number}.",
    )
    return new_payment

@router.post("/run-sla-checks")
def trigger_sla_delivery_alerts(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    return scheduler.run_sla_delivery_checks(db)

@router.put("/deliveries/{payment_id}/complete", response_model=schemas.PaymentResponse)
def mark_delivery_completed(
    payment_id: int,
    db: Session = Depends(get_db),
    admin: user_models.User = Depends(require_roles("ADMIN")),
):
    order = db.query(models.PaymentAndDelivery).filter(models.PaymentAndDelivery.id == payment_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment/Delivery record not found")
    if order.is_delivered:
        raise HTTPException(status_code=400, detail="Delivery has already been confirmed")

    order.is_delivered = True

    # Update parent requisition status to COMPLETED
    quote = db.query(tender_models.SupplierQuotation).filter(
        tender_models.SupplierQuotation.id == order.quotation_id
    ).first()
    if quote:
        req = db.query(req_models.Requisition).filter(req_models.Requisition.id == quote.requisition_id).first()
        if req:
            if order.quotation_line_id is not None:
                quote_line = db.query(tender_models.SupplierQuotationLine).filter(
                    tender_models.SupplierQuotationLine.id == order.quotation_line_id
                ).first()
                if quote_line:
                    request_item = db.query(req_models.RequisitionItem).filter(
                        req_models.RequisitionItem.id == quote_line.requisition_item_id
                    ).first()
                    if request_item:
                        request_item.status = "COMPLETED"
                refresh_requisition_status(db, req)
            else:
                req.status = "COMPLETED"

    audit.record(db, admin, "DELIVERY_COMPLETED", "payment", order.id)
    db.commit()
    db.refresh(order)
    return order

@router.get("/", response_model=List[schemas.PaymentResponse])
def get_all_payments_and_deliveries(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    payments = db.query(models.PaymentAndDelivery).order_by(models.PaymentAndDelivery.id.desc()).all()
    result = []
    for payment in payments:
        row = schemas.PaymentResponse.model_validate(payment).model_dump()
        quote = db.query(tender_models.SupplierQuotation).filter(
            tender_models.SupplierQuotation.id == payment.quotation_id
        ).first()
        row["supplier_name"] = quote.supplier_name if quote else None
        if payment.quotation_line_id:
            quote_line = db.query(tender_models.SupplierQuotationLine).filter(
                tender_models.SupplierQuotationLine.id == payment.quotation_line_id
            ).first()
            request_item = db.query(req_models.RequisitionItem).filter(
                req_models.RequisitionItem.id == quote_line.requisition_item_id
            ).first() if quote_line else None
            item = db.query(inv_models.InventoryItem).filter(
                inv_models.InventoryItem.id == request_item.item_id
            ).first() if request_item else None
            row["item_name"] = item.item_name if item else None
        result.append(row)
    return result

@router.get("/audit-logs", response_model=List[schemas.AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    return db.query(audit.AuditLog).order_by(audit.AuditLog.id.desc()).all()

