import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from src.app.database import Base


class Remark(Base):
    __tablename__ = "remarks"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), nullable=False)
    subject = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    related_ref = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING_REVIEW")
    admin_response = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class RemarkAttachment(Base):
    __tablename__ = "remark_attachments"

    id = Column(Integer, primary_key=True, index=True)
    remark_id = Column(Integer, ForeignKey("remarks.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    data = Column(LargeBinary, nullable=False)
