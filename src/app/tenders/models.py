from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from src.app.database import Base

class SupplierQuotation(Base):
    __tablename__ = "supplier_quotations"

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    supplier_name = Column(String(100), nullable=False)
    supplier_email = Column(String(100), nullable=False)
    supplier_phone = Column(String(50), nullable=False)

    quoted_item_description = Column(String(200), nullable=False)
    total_price = Column(Float, nullable=False)
    expected_delivery_date = Column(DateTime, nullable=False)

    ai_flag_notes = Column(String(255), nullable=True)
    is_approved_lowest = Column(Boolean, default=False)
