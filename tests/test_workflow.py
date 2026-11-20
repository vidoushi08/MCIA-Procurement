from src.app.database import SessionLocal
from src.app import notifications
from src.app.users.models import User
from src.app.security import hash_password
from tests.conftest import login, PASSWORD

real_send_email = notifications.send_email


def item_id(name):
    db = SessionLocal()
    try:
        from src.app.inventory.models import InventoryItem
        return db.query(InventoryItem).filter(InventoryItem.item_name == name).first().id
    finally:
        db.close()


def staff_id(email):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first().id
    finally:
        db.close()


def submit(client, email, item, qty):
    sid = staff_id(email)
    return client.post(
        "/requisitions/",
        json={"staff_id": sid, "item_id": item_id(item), "quantity_requested": qty},
        headers=login(client, email),
    )


def capture_emails(monkeypatch):
    from src.app import notifications

    sent = []
    monkeypatch.setattr(
        notifications,
        "send_email",
        lambda to, subject, body: sent.append(
            {"to": to, "subject": subject, "body": body}
        ) or True,
    )
    return sent


def test_login_ok_and_wrong_password(seeded):
    ok = seeded.post("/auth/login", json={"email": "staff@test.com", "password": PASSWORD})
    assert ok.status_code == 200
    assert "password_hash" not in ok.json()["user"]
    bad = seeded.post("/auth/login", json={"email": "staff@test.com", "password": "wrong-pass"})
    assert bad.status_code == 401


def test_protected_route_requires_token(seeded):
    assert seeded.get("/requisitions/").status_code == 401


def test_staff_cannot_sign_as_head(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 10).json()
    resp = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "staff@test.com"))
    assert resp.status_code == 403


def test_new_requisition_notifies_heads_in_staff_department(seeded, monkeypatch):
    sent = capture_emails(monkeypatch)
    db = SessionLocal()
    try:
        db.add(User(
            full_name="Operations Head",
            email="operations.head@test.com",
            department="Operations",
            role="DEPT_HEAD",
            password_hash=hash_password(PASSWORD),
        ))
        db.commit()
    finally:
        db.close()

    response = submit(seeded, "staff@test.com", "A4 Paper", 5)

    assert response.status_code == 200
    assert [email["to"] for email in sent] == ["head@test.com"]
    assert "REQ-0001" in sent[0]["subject"]
    assert "A4 Paper × 5" in sent[0]["body"]


def test_head_approval_notifies_requesting_staff(seeded, monkeypatch):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    sent = capture_emails(monkeypatch)

    response = seeded.put(
        f"/requisitions/{req['id']}/sign-head",
        headers=login(seeded, "head@test.com"),
    )

    assert response.status_code == 200
    assert [email["to"] for email in sent] == ["staff@test.com"]
    assert "approved by Department Head" in sent[0]["subject"]


def test_stock_flow_deducts_when_enough(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 10).json()
    seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    resp = seeded.put(f"/requisitions/{req['id']}/sign-admin", headers=login(seeded, "admin@test.com"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "FULFILLED_FROM_STOCK"
    db = SessionLocal()
    try:
        from src.app.inventory.models import InventoryItem
        assert db.query(InventoryItem).filter(InventoryItem.item_name == "A4 Paper").first().quantity_in_stock == 40
    finally:
        db.close()


def test_stock_flow_opens_tender_when_short(seeded):
    req = submit(seeded, "staff@test.com", "Stapler", 10).json()
    seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert seeded.put(f"/requisitions/{req['id']}/sign-admin",
                      headers=login(seeded, "admin@test.com")).status_code == 400


def test_multi_item_request_uses_stock_for_available_lines_and_quotes_for_short_lines(seeded):
    payload = {
        "staff_id": staff_id("staff@test.com"),
        "items": [
            {"item_id": item_id("A4 Paper"), "quantity_requested": 10},
            {"item_id": item_id("Stapler"), "quantity_requested": 2},
        ],
    }
    created = seeded.post("/requisitions/", json=payload, headers=login(seeded, "staff@test.com"))
    assert created.status_code == 200
    req = created.json()
    assert len(req["items"]) == 2
    assert req["head_approval_status"] == "Pending"
    assert req["admin_approval_status"] == "Pending"

    head = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert head.status_code == 200
    assert head.json()["status"] == "PENDING_QUOTES"
    assert head.json()["head_approval_status"] == "Approved"
    assert head.json()["admin_approval_status"] == "Pending"
    assert seeded.put(f"/requisitions/{req['id']}/sign-admin",
                      headers=login(seeded, "admin@test.com")).status_code == 400

    requested = {line["item_name"]: line for line in head.json()["items"]}
    assert requested["A4 Paper"]["status"] == "PENDING_ADMIN"
    assert requested["Stapler"]["status"] == "PENDING_QUOTES"
    quote_id = add_quote(seeded, req["id"], 120.0, requested["Stapler"]["id"])
    submitted = seeded.put(f"/requisitions/{req['id']}/submit-quotes",
                           headers=login(seeded, "staff@test.com"))
    assert submitted.status_code == 200
    matrix = seeded.get(f"/tenders/requisition/{req['id']}/ai-matrix",
                        headers=login(seeded, "admin@test.com"))
    assert matrix.status_code == 200
    signed = seeded.put(f"/requisitions/{req['id']}/sign-admin",
                        headers=login(seeded, "admin@test.com"))
    assert signed.status_code == 200 and signed.json()["status"] == "TENDER_OPEN"
    assert signed.json()["admin_approval_status"] == "Approved"
    lines = {line["item_name"]: line for line in signed.json()["items"]}
    assert lines["A4 Paper"]["status"] == "FULFILLED_FROM_STOCK"
    assert lines["Stapler"]["status"] == "TENDER_OPEN"

    db = SessionLocal()
    try:
        from src.app.inventory.models import InventoryItem
        assert db.query(InventoryItem).filter(
            InventoryItem.item_name == "A4 Paper"
        ).first().quantity_in_stock == 40
        assert db.query(InventoryItem).filter(
            InventoryItem.item_name == "Stapler"
        ).first().quantity_in_stock == 0
    finally:
        db.close()
    assert quote_id > 0


def test_supplier_package_can_cover_selected_lines_and_admin_receives_comparison(seeded):
    from src.app.inventory.models import InventoryItem

    db = SessionLocal()
    try:
        db.add(InventoryItem(item_name="Pens", quantity_in_stock=0, department_category="Finance"))
        db.commit()
    finally:
        db.close()

    created = seeded.post("/requisitions/", json={
        "staff_id": staff_id("staff@test.com"),
        "items": [
            {"item_id": item_id("Stapler"), "quantity_requested": 4},
            {"item_id": item_id("Pens"), "quantity_requested": 12},
        ],
    }, headers=login(seeded, "staff@test.com"))
    assert created.status_code == 200
    req = created.json()
    head = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert head.json()["status"] == "PENDING_QUOTES"
    line_ids = {line["item_name"]: line["id"] for line in head.json()["items"]}

    partial_package = {
        "requisition_id": req["id"],
        "supplier_name": "Office Supply Co",
        "supplier_email": "sales@officeco.com",
        "supplier_phone": "5550000",
        "expected_delivery_date": "2030-01-10T00:00:00",
        "lines": [{
            "requisition_item_id": line_ids["Stapler"],
            "quoted_item_description": "Staplers, 4 units",
            "total_price": 400,
        }],
    }
    first = seeded.post("/tenders/quotations", json=partial_package,
                        headers=login(seeded, "staff@test.com"))
    assert first.status_code == 200 and len(first.json()["lines"]) == 1
    assert seeded.put(f"/requisitions/{req['id']}/submit-quotes",
                      headers=login(seeded, "staff@test.com")).status_code == 400

    full_package = {**partial_package, "supplier_name": "Second Supplier",
                    "supplier_email": "quotes@secondco.com",
                    "lines": [
                        partial_package["lines"][0],
                        {
                            "requisition_item_id": line_ids["Pens"],
                            "quoted_item_description": "Pens, 12 boxes",
                            "total_price": 240,
                        },
                    ]}
    second = seeded.post("/tenders/quotations", json=full_package,
                         headers=login(seeded, "staff@test.com"))
    assert second.status_code == 200 and len(second.json()["lines"]) == 2
    sent = seeded.put(f"/requisitions/{req['id']}/submit-quotes",
                      headers=login(seeded, "staff@test.com"))
    assert sent.status_code == 200 and sent.json()["status"] == "PENDING_ADMIN"

    matrix = seeded.get(f"/tenders/requisition/{req['id']}/ai-matrix",
                        headers=login(seeded, "admin@test.com"))
    assert matrix.status_code == 200
    signed = seeded.put(f"/requisitions/{req['id']}/sign-admin",
                        headers=login(seeded, "admin@test.com"))
    assert signed.status_code == 200 and signed.json()["status"] == "TENDER_OPEN"
    matrix = seeded.get(f"/tenders/requisition/{req['id']}/ai-matrix",
                        headers=login(seeded, "admin@test.com"))
    assert matrix.status_code == 200
    assert {line["item_name"] for line in matrix.json()} == {"Stapler", "Pens"}
    assert all(len(line["quotation_lines"]) >= 1 for line in matrix.json())


def test_legacy_requisition_and_quote_backfill_is_idempotent(seeded):
    import datetime
    from src.app.database import backfill_legacy_procurement_lines
    from src.app.requisitions.models import Requisition, RequisitionItem
    from src.app.tenders.models import SupplierQuotation, SupplierQuotationLine

    db = SessionLocal()
    try:
        legacy = Requisition(
            staff_id=staff_id("staff@test.com"),
            item_id=item_id("Stapler"),
            quantity_requested=3,
            status="TENDER_OPEN",
            head_signed=True,
            admin_signed=True,
        )
        db.add(legacy)
        db.flush()
        quote = SupplierQuotation(
            requisition_id=legacy.id,
            supplier_name="Legacy Supplier",
            supplier_email="legacy@example.com",
            supplier_phone="5551111",
            quoted_item_description="Stapler, 3 units",
            total_price=90,
            expected_delivery_date=datetime.datetime(2030, 1, 10),
        )
        db.add(quote)
        db.commit()
        req_id = legacy.id
        quote_id = quote.id
    finally:
        db.close()

    backfill_legacy_procurement_lines()
    backfill_legacy_procurement_lines()

    db = SessionLocal()
    try:
        request_lines = db.query(RequisitionItem).filter(
            RequisitionItem.requisition_id == req_id
        ).all()
        quote_lines = db.query(SupplierQuotationLine).filter(
            SupplierQuotationLine.quotation_id == quote_id
        ).all()
        assert len(request_lines) == 1
        assert request_lines[0].status == "TENDER_OPEN"
        assert len(quote_lines) == 1
        assert quote_lines[0].requisition_item_id == request_lines[0].id
    finally:
        db.close()


def test_admin_cannot_sign_before_head(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    resp = seeded.put(f"/requisitions/{req['id']}/sign-admin", headers=login(seeded, "admin@test.com"))
    assert resp.status_code == 400


def test_head_from_other_department_is_forbidden(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    db = SessionLocal()
    try:
        db.add(User(full_name="Ops Head", email="opshead@test.com", department="Operations",
                    role="DEPT_HEAD", password_hash=hash_password(PASSWORD)))
        db.commit()
    finally:
        db.close()
    resp = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "opshead@test.com"))
    assert resp.status_code == 403


def test_staff_cannot_view_another_staffs_progress(seeded):
    other_id = staff_id("other@test.com")
    resp = seeded.get(f"/requisitions/staff/{other_id}/progress", headers=login(seeded, "staff@test.com"))
    assert resp.status_code == 403


def open_tender(client, item, qty, prices=(120.0,), compare=True, sign=True):
    req = submit(client, "staff@test.com", item, qty).json()
    head_resp = client.put(f"/requisitions/{req['id']}/sign-head", headers=login(client, "head@test.com"))
    assert head_resp.status_code == 200
    line_id = req["items"][0]["id"]
    req["quotation_line_ids"] = [
        add_quote(client, req["id"], price, line_id) for price in prices
    ]
    submitted = client.put(f"/requisitions/{req['id']}/submit-quotes",
                           headers=login(client, "staff@test.com"))
    assert submitted.status_code == 200, submitted.text
    if compare:
        matrix = client.get(f"/tenders/requisition/{req['id']}/ai-matrix",
                            headers=login(client, "admin@test.com"))
        assert matrix.status_code == 200, matrix.text
    if sign:
        signed = client.put(f"/requisitions/{req['id']}/sign-admin",
                            headers=login(client, "admin@test.com"))
        assert signed.status_code == 200 and signed.json()["status"] == "TENDER_OPEN"
    return req


def test_quote_submission_notifies_administrators(seeded, monkeypatch):
    req = submit(seeded, "staff@test.com", "Stapler", 10).json()
    head = seeded.put(
        f"/requisitions/{req['id']}/sign-head",
        headers=login(seeded, "head@test.com"),
    )
    assert head.status_code == 200
    add_quote(seeded, req["id"], 120.0, req["items"][0]["id"])
    sent = capture_emails(monkeypatch)

    response = seeded.put(
        f"/requisitions/{req['id']}/submit-quotes",
        headers=login(seeded, "staff@test.com"),
    )

    assert response.status_code == 200
    assert [email["to"] for email in sent] == ["admin@test.com"]
    assert "REQ-0001" in sent[0]["subject"]
    assert "comparative table" in sent[0]["body"]


def test_admin_approval_notifies_requesting_staff(seeded, monkeypatch):
    req = open_tender(seeded, "Stapler", 10, sign=False)
    sent = capture_emails(monkeypatch)

    response = seeded.put(
        f"/requisitions/{req['id']}/sign-admin",
        headers=login(seeded, "admin@test.com"),
    )

    assert response.status_code == 200
    assert [email["to"] for email in sent] == ["staff@test.com"]
    assert "approved by Administrator" in sent[0]["subject"]


def quote_payload(req_id, price, line_id):
    return {
        "requisition_id": req_id,
        "supplier_name": "Paper Co",
        "supplier_email": "sales@paperco.com",
        "supplier_phone": "5555555",
        "expected_delivery_date": "2030-01-10T00:00:00",
        "lines": [{
            "requisition_item_id": line_id,
            "quoted_item_description": "Stapler, 10 pack",
            "total_price": price,
        }],
    }


def test_open_tenders_list_quotes(seeded):
    req = open_tender(seeded, "Stapler", 10)
    resp = seeded.get("/tenders/open", headers=login(seeded, "admin@test.com"))
    assert resp.status_code == 200
    tenders = resp.json()
    assert len(tenders) == 1
    assert tenders[0]["requisition_id"] == req["id"]
    assert tenders[0]["items"][0]["item_name"] == "Stapler"
    assert len(tenders[0]["items"][0]["quotation_lines"]) == 1


def test_admin_must_generate_comparison_before_signing_quotes(seeded):
    req = open_tender(seeded, "Stapler", 10, compare=False, sign=False)
    headers = login(seeded, "admin@test.com")

    blocked = seeded.put(f"/requisitions/{req['id']}/sign-admin", headers=headers)
    assert blocked.status_code == 400
    assert "comparative table" in blocked.json()["detail"]

    comparison = seeded.get(
        f"/tenders/requisition/{req['id']}/ai-matrix", headers=headers
    )
    assert comparison.status_code == 200

    signed = seeded.put(f"/requisitions/{req['id']}/sign-admin", headers=headers)
    assert signed.status_code == 200
    assert signed.json()["comparison_generated_at"] is not None


def test_quote_rejected_when_not_open_for_tender(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    resp = seeded.post("/tenders/quotations", json=quote_payload(req["id"], 50.0, req["items"][0]["id"]),
                       headers=login(seeded, "staff@test.com"))
    assert resp.status_code == 400


def add_quote(client, req_id, price, line_id):
    resp = client.post("/tenders/quotations", json=quote_payload(req_id, price, line_id),
                       headers=login(client, "staff@test.com"))
    assert resp.status_code == 200, resp.text
    return resp.json()["lines"][0]["id"]


def mark_compliant(quote_ids):
    db = SessionLocal()
    try:
        from src.app.tenders.models import SupplierQuotationLine
        for qid in quote_ids:
            db.query(SupplierQuotationLine).filter(SupplierQuotationLine.id == qid).update({"is_compliant": True})
        db.commit()
    finally:
        db.close()


def pay(client, quote_id, cheque, amount=100.0):
    return client.post("/finance/approve-and-pay",
                       json={"quotation_line_id": quote_id, "cheque_number": cheque, "amount_paid": amount},
                       headers=login(client, "admin@test.com"))


def test_payment_requires_compliant_quote(seeded):
    req = open_tender(seeded, "Stapler", 10)
    qid = req["quotation_line_ids"][0]
    assert pay(seeded, qid, "CHQ-1").status_code == 400


def test_payment_notifies_supplier(seeded, monkeypatch):
    req = open_tender(seeded, "Stapler", 10)
    quote_line_id = req["quotation_line_ids"][0]
    mark_compliant([quote_line_id])
    sent = capture_emails(monkeypatch)

    response = pay(seeded, quote_line_id, "CHQ-MAIL", amount=120.0)

    assert response.status_code == 200
    assert [email["to"] for email in sent] == ["sales@paperco.com"]
    assert "payment recorded" in sent[0]["subject"].lower()
    assert "CHQ-MAIL" in sent[0]["body"]


def test_smtp_failure_is_logged_and_reported(monkeypatch, caplog):
    import smtplib

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "procurement@example.com")
    monkeypatch.setenv("SMTP_PORT", "587")

    class FailedSMTP:
        def __init__(self, host, port, timeout):
            raise smtplib.SMTPConnectError(421, "Connection refused")

    monkeypatch.setattr(notifications.smtplib, "SMTP", FailedSMTP)

    assert real_send_email(
        "staff@example.com", "Test notification", "Test body"
    ) is False
    assert "SMTP delivery failed" in caplog.text


def test_ai_matrix_sets_compliance_from_gemini_verdict(seeded, monkeypatch):
    from types import SimpleNamespace
    from src.app.tenders import ai_engine

    replies = iter(["MATCH stapler pack as requested.", "MISMATCH this is a hole punch."])

    class FakeModels:
        def generate_content(self, model, contents):
            return SimpleNamespace(text=next(replies))

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(ai_engine.genai, "Client", FakeClient)
    req = open_tender(seeded, "Stapler", 10, prices=(100.0, 150.0),
                      compare=False, sign=False)
    matrix = seeded.get(f"/tenders/requisition/{req['id']}/ai-matrix", headers=login(seeded, "admin@test.com")).json()
    lines = matrix[0]["quotation_lines"]
    assert [line["is_compliant"] for line in lines] == [True, False]
    assert lines[1]["ai_flag_notes"] == "this is a hole punch."


def test_ai_matrix_local_fallback_without_key(seeded, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    req = open_tender(seeded, "Stapler", 10, prices=(100.0,))
    matrix = seeded.get(f"/tenders/requisition/{req['id']}/ai-matrix", headers=login(seeded, "admin@test.com")).json()
    line = matrix[0]["quotation_lines"][0]
    assert line["is_compliant"] is True
    assert line["ai_flag_notes"] == "Verified match (Local Rule Check)."


def test_only_lowest_compliant_quote_can_be_paid(seeded):
    req = open_tender(seeded, "Stapler", 10, prices=(100.0, 150.0))
    cheap, dear = req["quotation_line_ids"]
    mark_compliant([cheap, dear])
    assert pay(seeded, dear, "CHQ-2").status_code == 400
    assert pay(seeded, cheap, "CHQ-3").status_code == 200


def test_duplicate_cheque_and_second_payment_rejected(seeded):
    req = open_tender(seeded, "Stapler", 10, prices=(100.0,))
    qid = req["quotation_line_ids"][0]
    mark_compliant([qid])
    assert pay(seeded, qid, "CHQ-4").status_code == 200
    assert pay(seeded, qid, "CHQ-4").status_code == 400
    assert pay(seeded, qid, "CHQ-5").status_code == 400


def test_overdue_delivery_flags_phone_followup_once(seeded, monkeypatch):
    import datetime
    from src.app import notifications
    from src.app.finance import scheduler, models as finance_models
    from src.app.tenders.models import SupplierQuotation, SupplierQuotationLine

    sent = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, body: sent.append(to) or True)

    req = open_tender(seeded, "Stapler", 10, prices=(100.0,))
    qid = req["quotation_line_ids"][0]
    mark_compliant([qid])
    payment_id = pay(seeded, qid, "CHQ-7").json()["id"]
    sent.clear()

    db = SessionLocal()
    try:
        quote_line = db.query(SupplierQuotationLine).filter(SupplierQuotationLine.id == qid).first()
        db.query(SupplierQuotation).filter(SupplierQuotation.id == quote_line.quotation_id).update(
            {"expected_delivery_date": datetime.datetime.utcnow() - datetime.timedelta(days=1)})
        db.commit()
        first = scheduler.run_sla_delivery_checks(db)
        second = scheduler.run_sla_delivery_checks(db)
        order = db.query(finance_models.PaymentAndDelivery).filter(finance_models.PaymentAndDelivery.id == payment_id).first()
        assert order.phone_followup_required is True
        assert order.overdue_alert_sent is True
    finally:
        db.close()
    assert len(first["alerts_triggered"]) == 1
    assert second["alerts_triggered"] == []
    assert sent == ["sales@paperco.com"]


def test_sla_retries_reminder_when_smtp_fails(seeded, monkeypatch):
    import datetime
    from src.app import notifications
    from src.app.finance import models as finance_models, scheduler
    from src.app.tenders.models import SupplierQuotation, SupplierQuotationLine

    attempts = []
    monkeypatch.setattr(
        notifications,
        "send_email",
        lambda to, subject, body: attempts.append(to) or False,
    )
    req = open_tender(seeded, "Stapler", 10)
    quote_line_id = req["quotation_line_ids"][0]
    mark_compliant([quote_line_id])
    payment_id = pay(seeded, quote_line_id, "CHQ-RETRY", amount=120.0).json()["id"]
    attempts.clear()

    db = SessionLocal()
    try:
        quote_line = db.query(SupplierQuotationLine).filter(
            SupplierQuotationLine.id == quote_line_id
        ).first()
        quote = db.query(SupplierQuotation).filter(
            SupplierQuotation.id == quote_line.quotation_id
        ).first()
        quote.expected_delivery_date = (
            datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        )
        db.commit()

        first = scheduler.run_sla_delivery_checks(db)
        order = db.query(finance_models.PaymentAndDelivery).filter(
            finance_models.PaymentAndDelivery.id == payment_id
        ).first()
        assert order.pre_delivery_reminder_sent is False
        second = scheduler.run_sla_delivery_checks(db)
    finally:
        db.close()

    assert len(first["alerts_triggered"]) == 1
    assert "Email not sent" in first["alerts_triggered"][0]
    assert len(second["alerts_triggered"]) == 1
    assert attempts == ["sales@paperco.com", "sales@paperco.com"]


def test_delivery_completes_once_and_is_audited(seeded):
    req = open_tender(seeded, "Stapler", 10, prices=(100.0,))
    qid = req["quotation_line_ids"][0]
    mark_compliant([qid])
    payment_id = pay(seeded, qid, "CHQ-6").json()["id"]
    done = seeded.put(f"/finance/deliveries/{payment_id}/complete", headers=login(seeded, "admin@test.com"))
    assert done.status_code == 200 and done.json()["is_delivered"] is True
    assert seeded.put(f"/finance/deliveries/{payment_id}/complete",
                      headers=login(seeded, "admin@test.com")).status_code == 400
    logs = seeded.get("/finance/audit-logs", headers=login(seeded, "admin@test.com")).json()
    actions = {entry["action"] for entry in logs}
    assert {"QUOTE_SUBMITTED", "PAYMENT_APPROVED", "DELIVERY_COMPLETED"} <= actions


def test_head_cannot_sign_twice(seeded):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    assert req["staff_signed_at"] is not None
    first = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert first.status_code == 200
    again = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert again.status_code == 400


def test_head_can_decline_with_reason(seeded, monkeypatch):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    sent = capture_emails(monkeypatch)
    no_reason = seeded.put(f"/requisitions/{req['id']}/decline", json={"reason": "no"},
                           headers=login(seeded, "head@test.com"))
    assert no_reason.status_code == 422
    resp = seeded.put(f"/requisitions/{req['id']}/decline", json={"reason": "Not needed this quarter"},
                      headers=login(seeded, "head@test.com"))
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "DECLINED"
    assert body["decline_reason"] == "Not needed this quarter"
    assert body["declined_at"] is not None
    assert [email["to"] for email in sent] == ["staff@test.com"]
    assert "declined by Department Head" in sent[0]["subject"]
    sign = seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    assert sign.status_code == 400


def test_admin_declines_only_at_admin_stage(seeded, monkeypatch):
    req = submit(seeded, "staff@test.com", "A4 Paper", 5).json()
    early = seeded.put(f"/requisitions/{req['id']}/decline", json={"reason": "Too early"},
                       headers=login(seeded, "admin@test.com"))
    assert early.status_code == 400
    seeded.put(f"/requisitions/{req['id']}/sign-head", headers=login(seeded, "head@test.com"))
    sent = capture_emails(monkeypatch)
    late = seeded.put(f"/requisitions/{req['id']}/decline", json={"reason": "Over budget"},
                      headers=login(seeded, "admin@test.com"))
    assert late.status_code == 200
    assert late.json()["status"] == "DECLINED"
    assert [email["to"] for email in sent] == ["staff@test.com"]
    assert "declined by Administrator" in sent[0]["subject"]


def test_dept_head_sees_only_own_department_with_names(seeded):
    submit(seeded, "staff@test.com", "A4 Paper", 5)
    created = seeded.post(
        "/users/",
        json={"full_name": "Other Head", "email": "otherhead@test.com", "department": "Estates",
              "role": "DEPT_HEAD", "password": PASSWORD},
        headers=login(seeded, "admin@test.com"),
    )
    assert created.status_code == 200
    other = seeded.get("/requisitions/", headers=login(seeded, "otherhead@test.com")).json()
    assert other == []
    mine = seeded.get("/requisitions/", headers=login(seeded, "head@test.com")).json()
    assert mine and mine[0]["item_name"] == "A4 Paper" and mine[0]["staff_name"]
    everything = seeded.get("/requisitions/", headers=login(seeded, "admin@test.com")).json()
    assert len(everything) >= len(mine)


def test_remarks_submit_review_and_access(seeded):
    body = {"category": "Delivery delay", "subject": "Paper not delivered",
            "description": "The paper ordered last week has not arrived yet."}
    short = seeded.post("/remarks/", json={**body, "description": "short"}, headers=login(seeded, "staff@test.com"))
    assert short.status_code == 422
    created = seeded.post("/remarks/", json=body, headers=login(seeded, "staff@test.com"))
    assert created.status_code == 200
    remark = created.json()
    assert remark["status"] == "PENDING_REVIEW" and remark["staff_name"]
    mine = seeded.get("/remarks/mine", headers=login(seeded, "staff@test.com")).json()
    assert [r["id"] for r in mine] == [remark["id"]]
    assert seeded.get("/remarks/", headers=login(seeded, "staff@test.com")).status_code == 403
    update = seeded.put(f"/remarks/{remark['id']}/status",
                        json={"status": "RESOLVED", "admin_response": "Supplier confirmed delivery."},
                        headers=login(seeded, "admin@test.com"))
    assert update.status_code == 200
    assert update.json()["status"] == "RESOLVED"
    bad = seeded.put(f"/remarks/{remark['id']}/status", json={"status": "CLOSED"},
                     headers=login(seeded, "admin@test.com"))
    assert bad.status_code == 400


def test_remark_attachments_upload_validate_and_download(seeded):
    staff = login(seeded, "staff@test.com")
    body = {"category": "Other", "subject": "Damaged box", "description": "The delivered box arrived crushed."}
    remark = seeded.post("/remarks/", json=body, headers=staff).json()
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    uploaded = seeded.post(f"/remarks/{remark['id']}/attachments",
                           files=[("files", ("photo.png", png, "image/png"))], headers=staff)
    assert uploaded.status_code == 200
    attachment = uploaded.json()["attachments"][0]
    assert attachment["filename"] == "photo.png" and attachment["size"] == len(png)
    fake = seeded.post(f"/remarks/{remark['id']}/attachments",
                       files=[("files", ("fake.pdf", b"not really a pdf", "application/pdf"))], headers=staff)
    assert fake.status_code == 400
    exe = seeded.post(f"/remarks/{remark['id']}/attachments",
                      files=[("files", ("run.exe", b"MZ", "application/octet-stream"))], headers=staff)
    assert exe.status_code == 400
    download = seeded.get(f"/remarks/attachments/{attachment['id']}", headers=login(seeded, "admin@test.com"))
    assert download.status_code == 200 and download.content == png
