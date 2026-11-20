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
    },
    "supplier_quotations": {"is_compliant": "BOOLEAN NULL"},
    "payment_and_delivery": {"phone_followup_required": "BOOLEAN NULL"},
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
