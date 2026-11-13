from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RequisitionCreate(BaseModel):
    staff_id: int
    item_id: int
    quantity_requested: int = Field(gt=0)

class RequisitionResponse(BaseModel):
    id: int
    staff_id: int
    item_id: int
    quantity_requested: int
    staff_signed: bool
    head_signed: bool
    head_signed_at: Optional[datetime] = None
    admin_signed: bool
    admin_signed_at: Optional[datetime] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
