import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from src.app.database import Base


class AuditLog(Base):
    """Append-only record of payments, quotations and deliveries. No update or delete endpoints exist."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, nullable=True)
    actor_role = Column(String(20), nullable=True)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


def record(db: Session, actor, action: str, entity: str, entity_id: int | None, details: str | None = None):
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details[:255] if details else None,
    ))
