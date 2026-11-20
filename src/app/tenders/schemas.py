from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class QuotationCreate(BaseModel):
    requisition_id: int
    supplier_name: str
    supplier_email: EmailStr
    supplier_phone: str
    quoted_item_description: str
    total_price: float
    expected_delivery_date: datetime

class QuotationResponse(QuotationCreate):
    id: int
    ai_flag_notes: Optional[str] = None
    is_compliant: Optional[bool] = None
    is_approved_lowest: bool

    class Config:
        from_attributes = True

class OpenTenderResponse(BaseModel):
    requisition_id: int
    item_name: str
    quantity_requested: int
    staff_id: int
    created_at: datetime
    quotations: List[QuotationResponse]
