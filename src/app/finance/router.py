from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.database import get_db
from src.app import audit
from src.app.security import require_roles
from src.app.finance import models, schemas, scheduler
from src.app.tenders import models as tender_models
from src.app.requisitions import models as req_models
from src.app.users import models as user_models

router = APIRouter(prefix="/finance", tags=["Cheque Payments & SLA Delivery"])

@router.post("/approve-and-pay", response_model=schemas.PaymentResponse)
def approve_quote_and_log_cheque(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    admin: user_models.User = Depends(require_roles("ADMIN")),
):
    quote = db.query(tender_models.SupplierQuotation).filter(
        tender_models.SupplierQuotation.id == payment.quotation_id
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Supplier quotation not found")

    req = db.query(req_models.Requisition).filter(
        req_models.Requisition.id == quote.requisition_id
    ).with_for_update().first()
    if req is None or req.status != "TENDER_OPEN":
        raise HTTPException(status_code=400, detail="Only requisitions open for tender can be paid")

    already_paid = db.query(models.PaymentAndDelivery).join(
        tender_models.SupplierQuotation,
        models.PaymentAndDelivery.quotation_id == tender_models.SupplierQuotation.id,
    ).filter(tender_models.SupplierQuotation.requisition_id == req.id).first()
    if already_paid:
        raise HTTPException(status_code=400, detail="This requisition has already been paid")

    if db.query(models.PaymentAndDelivery).filter(
        models.PaymentAndDelivery.cheque_number == payment.cheque_number
    ).first():
        raise HTTPException(status_code=400, detail="Cheque number has already been used")

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
        quotation_id=payment.quotation_id,
        cheque_number=payment.cheque_number,
        amount_paid=payment.amount_paid
    )
    db.add(new_payment)
    db.flush()
    req.status = "PAID_AWAITING_DELIVERY"
    audit.record(db, admin, "PAYMENT_APPROVED", "payment", new_payment.id,
                 f"Requisition {req.id}, quote {quote.id}, cheque {payment.cheque_number}, {payment.amount_paid}")
    db.commit()
    db.refresh(new_payment)
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
    return db.query(models.PaymentAndDelivery).all()

@router.get("/audit-logs", response_model=List[schemas.AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    return db.query(audit.AuditLog).order_by(audit.AuditLog.id.desc()).all()

