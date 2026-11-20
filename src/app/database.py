import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / "config" / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# create_all does not add columns to existing tables, so add newer columns here.
MISSING_COLUMNS = {
    "users": {"password_hash": "VARCHAR(255) NULL"},
    "requisitions": {
        "staff_signed_at": "DATETIME NULL",
        "declined_at": "DATETIME NULL",
        "decline_reason": "VARCHAR(255) NULL",
        "declined_by_role": "VARCHAR(20) NULL",
        "comparison_generated_at": "DATETIME NULL",
    },
    "supplier_quotations": {"is_compliant": "BOOLEAN NULL"},
    "payment_and_delivery": {
        "phone_followup_required": "BOOLEAN NULL",
        "quotation_line_id": "INTEGER NULL",
    },
}


def add_missing_columns():
    inspector = inspect(engine)
    for table, columns in MISSING_COLUMNS.items():
        if not inspector.has_table(table):
            continue
        existing = {col["name"] for col in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def backfill_legacy_procurement_lines():
    from src.app.requisitions.models import Requisition, RequisitionAuditLog, RequisitionItem
    from src.app.tenders.models import SupplierQuotation, SupplierQuotationLine

    db = SessionLocal()
    try:
        for req in db.query(Requisition).all():
            if req.status == "DECLINED" and not req.declined_by_role:
                decline_log = db.query(RequisitionAuditLog).filter(
                    RequisitionAuditLog.requisition_id == req.id,
                    RequisitionAuditLog.action == "DECLINED",
                ).order_by(RequisitionAuditLog.id.desc()).first()
                if decline_log and decline_log.details:
                    role = decline_log.details.split(":", 1)[0].strip().upper()
                    if role in {"DEPT_HEAD", "ADMIN"}:
                        req.declined_by_role = role
            has_lines = db.query(RequisitionItem.id).filter(
                RequisitionItem.requisition_id == req.id
            ).first()
            if has_lines:
                continue
            db.add(RequisitionItem(
                requisition_id=req.id,
                item_id=req.item_id,
                quantity_requested=req.quantity_requested,
                status=req.status,
            ))
        db.flush()

        for quote in db.query(SupplierQuotation).all():
            has_lines = db.query(SupplierQuotationLine.id).filter(
                SupplierQuotationLine.quotation_id == quote.id
            ).first()
            if has_lines:
                continue
            req_item = db.query(RequisitionItem).filter(
                RequisitionItem.requisition_id == quote.requisition_id
            ).order_by(RequisitionItem.id).first()
            if req_item:
                db.add(SupplierQuotationLine(
                    quotation_id=quote.id,
                    requisition_item_id=req_item.id,
                    quoted_item_description=quote.quoted_item_description,
                    total_price=quote.total_price,
                    ai_flag_notes=quote.ai_flag_notes,
                    is_compliant=quote.is_compliant,
                    is_approved_lowest=quote.is_approved_lowest,
                ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
