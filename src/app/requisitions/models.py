from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
import datetime
from src.app.database import Base

class Requisition(Base):
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)

    staff_signed = Column(Boolean, default=True)
    head_signed = Column(Boolean, default=False)
    head_signed_at = Column(DateTime, nullable=True)
    admin_signed = Column(Boolean, default=False)
    admin_signed_at = Column(DateTime, nullable=True)

    status = Column(String(50), default="PENDING_HEAD")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
