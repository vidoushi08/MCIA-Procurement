from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.database import get_db
from src.app.finance import models, schemas, scheduler
from src.app.tenders import models as tender_models
from src.app.requisitions import models as req_models

router = APIRouter(prefix="/finance", tags=["Cheque Payments & SLA Delivery"])

@router.post("/approve-and-pay", response_model=schemas.PaymentResponse)
def approve_quote_and_log_cheque(payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    quote = db.query(tender_models.SupplierQuotation).filter(
        tender_models.SupplierQuotation.id == payment.quotation_id
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Supplier quotation not found")

    # Mark quotation as approved lowest bid
    quote.is_approved_lowest = True

    new_payment = models.PaymentAndDelivery(
        quotation_id=payment.quotation_id,
        cheque_number=payment.cheque_number,
        amount_paid=payment.amount_paid
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    return new_payment

@router.post("/run-sla-checks")
def trigger_sla_delivery_alerts(db: Session = Depends(get_db)):
    return scheduler.run_sla_delivery_checks(db)

@router.put("/deliveries/{payment_id}/complete", response_model=schemas.PaymentResponse)
def mark_delivery_completed(payment_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PaymentAndDelivery).filter(models.PaymentAndDelivery.id == payment_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment/Delivery record not found")

    order.is_delivered = True

    # Update parent requisition status to COMPLETED
    quote = db.query(tender_models.SupplierQuotation).filter(
        tender_models.SupplierQuotation.id == order.quotation_id
    ).first()
    if quote:
        req = db.query(req_models.Requisition).filter(req_models.Requisition.id == quote.requisition_id).first()
        if req:
            req.status = "COMPLETED"

    db.commit()
    db.refresh(order)
    return order

@router.get("/", response_model=List[schemas.PaymentResponse])
def get_all_payments_and_deliveries(db: Session = Depends(get_db)):
    return db.query(models.PaymentAndDelivery).all()
