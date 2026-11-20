from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
import datetime
from src.app.database import Base

class PaymentAndDelivery(Base):
    __tablename__ = "payment_and_delivery"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("supplier_quotations.id"), nullable=False)
    cheque_number = Column(String(50), nullable=False)
    amount_paid = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.datetime.utcnow)

    pre_delivery_reminder_sent = Column(Boolean, default=False)
    overdue_alert_sent = Column(Boolean, default=False)
    phone_followup_required = Column(Boolean, default=False)
    is_delivered = Column(Boolean, default=False)
