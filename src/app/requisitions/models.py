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
    staff_signed_at = Column(DateTime, nullable=True)
    head_signed = Column(Boolean, default=False)
    head_signed_at = Column(DateTime, nullable=True)
    admin_signed = Column(Boolean, default=False)
    admin_signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(String(255), nullable=True)
    declined_by_role = Column(String(20), nullable=True)
    comparison_generated_at = Column(DateTime, nullable=True)

    status = Column(String(50), default="PENDING_HEAD")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class RequisitionItem(Base):
    __tablename__ = "requisition_items"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    status = Column(String(50), default="PENDING_HEAD", nullable=False)


class RequisitionAuditLog(Base):
    __tablename__ = "requisition_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
