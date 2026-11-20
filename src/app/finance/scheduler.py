import asyncio
import datetime
import logging
import os

from sqlalchemy.orm import Session

from src.app import notifications
from src.app.database import SessionLocal
from src.app.finance import models as finance_models
from src.app.tenders import models as tender_models

logger = logging.getLogger("mcia.sla")

def run_sla_delivery_checks(db: Session):
    now = datetime.datetime.utcnow()
    active_orders = db.query(finance_models.PaymentAndDelivery).filter(
        finance_models.PaymentAndDelivery.is_delivered == False
    ).all()

    alerts_triggered = []

    for order in active_orders:
        quote = db.query(tender_models.SupplierQuotation).filter(
            tender_models.SupplierQuotation.id == order.quotation_id
        ).first()
        if not quote:
            continue

        time_remaining = quote.expected_delivery_date - now

        # 1. Pre-Delivery Reminder (within 24 hours of due date)
        if datetime.timedelta(seconds=0) < time_remaining <= datetime.timedelta(hours=24):
            if not order.pre_delivery_reminder_sent:
                order.pre_delivery_reminder_sent = True
                notifications.send_email(
                    quote.supplier_email,
                    f"Delivery reminder for order #{order.id}",
                    f"Please confirm delivery for order #{order.id}, due {quote.expected_delivery_date:%Y-%m-%d}.",
                )
                alerts_triggered.append(
                    f"PRE-DELIVERY REMINDER: Order #{order.id} from {quote.supplier_name} is due within 24 hours."
                )

        # 2. Overdue Alert (due date has passed)
        elif time_remaining <= datetime.timedelta(seconds=0):
            if not order.overdue_alert_sent:
                order.overdue_alert_sent = True
                order.phone_followup_required = True
                notifications.send_email(
                    quote.supplier_email,
                    f"Overdue delivery for order #{order.id}",
                    f"Order #{order.id} was due {quote.expected_delivery_date:%Y-%m-%d} and is not yet delivered.",
                )
                alerts_triggered.append(
                    f"OVERDUE SLA ALERT: Email dispatched to {quote.supplier_email}. "
                    f"Flagged for phone follow-up at {quote.supplier_phone} ({quote.supplier_name})."
                )

    db.commit()
    return {"checked_orders": len(active_orders), "alerts_triggered": alerts_triggered}


def _run_checks_with_own_session():
    db = SessionLocal()
    try:
        return run_sla_delivery_checks(db)
    finally:
        db.close()


def interval_seconds_from_env() -> float:
    return max(float(os.getenv("SLA_CHECK_INTERVAL_MINUTES", "60")), 1.0) * 60


async def sla_check_loop(interval_seconds: float):
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            result = await asyncio.to_thread(_run_checks_with_own_session)
            for alert in result["alerts_triggered"]:
                logger.warning(alert)
        except Exception:
            logger.exception("Scheduled SLA check failed")
