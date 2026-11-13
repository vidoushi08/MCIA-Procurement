import datetime
from sqlalchemy.orm import Session
from src.app.finance import models as finance_models
from src.app.tenders import models as tender_models

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
                alerts_triggered.append(
                    f"PRE-DELIVERY REMINDER: Order #{order.id} from {quote.supplier_name} is due within 24 hours."
                )

        # 2. Overdue Alert (due date has passed)
        elif time_remaining <= datetime.timedelta(seconds=0):
            if not order.overdue_alert_sent:
                order.overdue_alert_sent = True
                alerts_triggered.append(
                    f"OVERDUE SLA ALERT: Email dispatched to {quote.supplier_email}. "
                    f"Flagged for phone follow-up at {quote.supplier_phone} ({quote.supplier_name})."
                )

    db.commit()
    return {"checked_orders": len(active_orders), "alerts_triggered": alerts_triggered}
