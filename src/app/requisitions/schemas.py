from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RequisitionItemCreate(BaseModel):
    item_id: int
    quantity_requested: int = Field(gt=0)


class RequisitionCreate(BaseModel):
    staff_id: int
    items: List[RequisitionItemCreate] = Field(default_factory=list)
    item_id: Optional[int] = None
    quantity_requested: Optional[int] = Field(default=None, gt=0)


class RequisitionItemResponse(BaseModel):
    id: int
    item_id: int
    quantity_requested: int
    status: str
    item_name: Optional[str] = None
    department_category: Optional[str] = None
    quotation_count: int = 0

    class Config:
        from_attributes = True

class DeclineRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)

class RequisitionResponse(BaseModel):
    id: int
    staff_id: int
    item_id: int
    quantity_requested: int
    staff_signed: bool
    staff_signed_at: Optional[datetime] = None
    head_signed: bool
    head_signed_at: Optional[datetime] = None
    admin_signed: bool
    admin_signed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    declined_by_role: Optional[str] = None
    comparison_generated_at: Optional[datetime] = None
    status: str
    created_at: datetime
    staff_name: Optional[str] = None
    department: Optional[str] = None
    item_name: Optional[str] = None
    items: List[RequisitionItemResponse] = Field(default_factory=list)
    head_approval_status: str = "Pending"
    admin_approval_status: str = "Pending"

    class Config:
        from_attributes = True
