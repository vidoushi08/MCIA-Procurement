from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PaymentCreate(BaseModel):
    quotation_id: Optional[int] = None
    quotation_line_id: Optional[int] = None
    cheque_number: str
    amount_paid: float

class PaymentResponse(PaymentCreate):
    id: int
    payment_date: datetime
    pre_delivery_reminder_sent: bool
    overdue_alert_sent: bool
    phone_followup_required: bool = False
    is_delivered: bool
    item_name: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: str
    entity: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
