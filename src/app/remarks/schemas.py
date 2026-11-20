from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

REMARK_STATUSES = ("PENDING_REVIEW", "IN_PROGRESS", "RESOLVED")


class RemarkCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    subject: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10)
    related_ref: Optional[str] = Field(default=None, max_length=50)


class RemarkStatusUpdate(BaseModel):
    status: str
    admin_response: Optional[str] = Field(default=None, max_length=500)


class AttachmentInfo(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int

    class Config:
        from_attributes = True


class RemarkResponse(BaseModel):
    id: int
    staff_id: int
    category: str
    subject: str
    description: str
    related_ref: Optional[str] = None
    status: str
    admin_response: Optional[str] = None
    created_at: datetime
    staff_name: Optional[str] = None
    attachments: List[AttachmentInfo] = []

    class Config:
        from_attributes = True
