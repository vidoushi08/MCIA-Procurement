from pydantic import BaseModel
from datetime import datetime

class PaymentCreate(BaseModel):
    quotation_id: int
    cheque_number: str
    amount_paid: float

class PaymentResponse(PaymentCreate):
    id: int
    payment_date: datetime
    pre_delivery_reminder_sent: bool
    overdue_alert_sent: bool
    is_delivered: bool

    class Config:
        from_attributes = True
