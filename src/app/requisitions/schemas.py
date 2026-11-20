from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RequisitionCreate(BaseModel):
    staff_id: int
    item_id: int
    quantity_requested: int = Field(gt=0)

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
    status: str
    created_at: datetime
    staff_name: Optional[str] = None
    department: Optional[str] = None
    item_name: Optional[str] = None

    class Config:
        from_attributes = True
