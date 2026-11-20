from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


class QuotationLineCreate(BaseModel):
    requisition_item_id: int
    quoted_item_description: str = Field(min_length=1, max_length=200)
    total_price: float = Field(gt=0)


class QuotationCreate(BaseModel):
    requisition_id: int
    supplier_name: str
    supplier_email: EmailStr
    supplier_phone: str
    expected_delivery_date: datetime
    lines: List[QuotationLineCreate] = Field(default_factory=list)
    quoted_item_description: Optional[str] = None
    total_price: Optional[float] = Field(default=None, gt=0)


class QuotationLineResponse(BaseModel):
    id: int
    quotation_id: int
    requisition_item_id: int
    item_name: Optional[str] = None
    quantity_requested: Optional[int] = None
    quoted_item_description: str
    total_price: float
    ai_flag_notes: Optional[str] = None
    is_compliant: Optional[bool] = None
    is_approved_lowest: bool
    is_lowest_compliant: bool = False
    supplier_name: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_phone: Optional[str] = None
    expected_delivery_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuotationResponse(BaseModel):
    id: int
    requisition_id: int
    supplier_name: str
    supplier_email: EmailStr
    supplier_phone: str
    expected_delivery_date: datetime
    quoted_item_description: str
    total_price: float
    ai_flag_notes: Optional[str] = None
    is_compliant: Optional[bool] = None
    is_approved_lowest: bool
    lines: List[QuotationLineResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ComparativeItemResponse(BaseModel):
    requisition_item_id: int
    item_name: str
    quantity_requested: int
    status: str
    quotation_lines: List[QuotationLineResponse] = Field(default_factory=list)


class OpenTenderResponse(BaseModel):
    requisition_id: int
    staff_id: int
    staff_name: str
    created_at: datetime
    items: List[ComparativeItemResponse] = Field(default_factory=list)
