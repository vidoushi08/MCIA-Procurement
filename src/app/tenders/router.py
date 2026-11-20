from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
from typing import List

from src.app import audit
from src.app.database import get_db
from src.app.inventory import models as inv_models
from src.app.requisitions import models as req_models
from src.app.security import require_roles
from src.app.tenders import ai_engine, models, schemas
from src.app.users import models as user_models

router = APIRouter(prefix="/tenders", tags=["Supplier Tenders & AI Comparison"])


def _legacy_items(db: Session, req: req_models.Requisition):
    rows = db.query(req_models.RequisitionItem).filter(
        req_models.RequisitionItem.requisition_id == req.id
    ).order_by(req_models.RequisitionItem.id).all()
    if rows:
        return rows
    row = req_models.RequisitionItem(
        requisition_id=req.id,
        item_id=req.item_id,
        quantity_requested=req.quantity_requested,
        status=req.status,
    )
    db.add(row)
    db.flush()
    return [row]


def _line_response(db: Session, line: models.SupplierQuotationLine, req_item=None):
    quote = db.query(models.SupplierQuotation).filter(
        models.SupplierQuotation.id == line.quotation_id
    ).first()
    request_item = req_item or db.query(req_models.RequisitionItem).filter(
        req_models.RequisitionItem.id == line.requisition_item_id
    ).first()
    item = db.query(inv_models.InventoryItem).filter(
        inv_models.InventoryItem.id == request_item.item_id
    ).first() if request_item else None
    return {
        "id": line.id,
        "quotation_id": line.quotation_id,
        "requisition_item_id": line.requisition_item_id,
        "item_name": item.item_name if item else "",
        "quantity_requested": request_item.quantity_requested if request_item else None,
        "quoted_item_description": line.quoted_item_description,
        "total_price": line.total_price,
        "ai_flag_notes": line.ai_flag_notes,
        "is_compliant": line.is_compliant,
        "is_approved_lowest": bool(line.is_approved_lowest),
        "is_lowest_compliant": False,
        "supplier_name": quote.supplier_name if quote else "",
        "supplier_email": quote.supplier_email if quote else "",
        "supplier_phone": quote.supplier_phone if quote else "",
        "expected_delivery_date": quote.expected_delivery_date if quote else None,
    }


def _comparative_item(db: Session, req_item: req_models.RequisitionItem, lines, lowest_id=None):
    item = db.query(inv_models.InventoryItem).filter(
        inv_models.InventoryItem.id == req_item.item_id
    ).first()
    responses = []
    for line in lines:
        row = _line_response(db, line, req_item)
        row["is_lowest_compliant"] = line.id == lowest_id
        responses.append(row)
    return {
        "requisition_item_id": req_item.id,
        "item_name": item.item_name if item else f"Item #{req_item.item_id}",
        "quantity_requested": req_item.quantity_requested,
        "status": req_item.status,
        "quotation_lines": sorted(responses, key=lambda row: row["total_price"]),
    }


@router.post("/quotations", response_model=schemas.QuotationResponse)
def submit_supplier_quotation(
    quote: schemas.QuotationCreate,
    db: Session = Depends(get_db),
    staff: user_models.User = Depends(require_roles("STAFF")),
):
    req = db.query(req_models.Requisition).filter(
        req_models.Requisition.id == quote.requisition_id
    ).with_for_update().first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.staff_id != staff.id:
        raise HTTPException(status_code=403, detail="Staff can only submit quotations for their own request")
    if req.status != "PENDING_QUOTES":
        raise HTTPException(status_code=400, detail="Department Head approval is required before entering quotations")

    request_items = _legacy_items(db, req)
    submitted_lines = quote.lines
    if not submitted_lines and quote.quoted_item_description and quote.total_price is not None:
        pending = [line for line in request_items if line.status == "PENDING_QUOTES"]
        if len(pending) != 1:
            raise HTTPException(status_code=422, detail="Select the request item lines covered by this supplier quote")
        submitted_lines = [schemas.QuotationLineCreate(
            requisition_item_id=pending[0].id,
            quoted_item_description=quote.quoted_item_description,
            total_price=quote.total_price,
        )]
    if not submitted_lines:
        raise HTTPException(status_code=422, detail="At least one request line must be included in a quotation")
    line_ids = [line.requisition_item_id for line in submitted_lines]
    if len(line_ids) != len(set(line_ids)):
        raise HTTPException(status_code=400, detail="A supplier quotation may include each request line only once")

    request_item_by_id = {line.id: line for line in request_items}
    for line in submitted_lines:
        if not line.quoted_item_description.strip():
            raise HTTPException(status_code=422, detail="Quoted item descriptions cannot be blank")
        request_item = request_item_by_id.get(line.requisition_item_id)
        if request_item is None:
            raise HTTPException(status_code=400, detail="A quoted line does not belong to this request")
        if request_item.status != "PENDING_QUOTES":
            raise HTTPException(status_code=400, detail="Only lines awaiting quotations may be quoted")

    summary = "; ".join(line.quoted_item_description for line in submitted_lines)[:200]
    total = sum(line.total_price for line in submitted_lines)
    new_quote = models.SupplierQuotation(
        requisition_id=quote.requisition_id,
        supplier_name=quote.supplier_name.strip(),
        supplier_email=str(quote.supplier_email),
        supplier_phone=quote.supplier_phone.strip(),
        quoted_item_description=summary,
        total_price=total,
        expected_delivery_date=quote.expected_delivery_date,
    )
    db.add(new_quote)
    db.flush()
    line_rows = []
    for line in submitted_lines:
        quote_line = models.SupplierQuotationLine(
            quotation_id=new_quote.id,
            requisition_item_id=line.requisition_item_id,
            quoted_item_description=line.quoted_item_description.strip(),
            total_price=line.total_price,
        )
        db.add(quote_line)
        line_rows.append(quote_line)
    audit.record(
        db,
        staff,
        "QUOTE_SUBMITTED",
        "quotation",
        new_quote.id,
        f"Requisition {quote.requisition_id}, {quote.supplier_name}, {len(line_rows)} line(s)",
    )
    db.commit()
    db.refresh(new_quote)
    return {
        "id": new_quote.id,
        "requisition_id": new_quote.requisition_id,
        "supplier_name": new_quote.supplier_name,
        "supplier_email": new_quote.supplier_email,
        "supplier_phone": new_quote.supplier_phone,
        "expected_delivery_date": new_quote.expected_delivery_date,
        "quoted_item_description": new_quote.quoted_item_description,
        "total_price": new_quote.total_price,
        "ai_flag_notes": new_quote.ai_flag_notes,
        "is_compliant": new_quote.is_compliant,
        "is_approved_lowest": bool(new_quote.is_approved_lowest),
        "lines": [_line_response(db, line) for line in line_rows],
    }


@router.get("/open", response_model=List[schemas.OpenTenderResponse])
def list_open_tenders(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    open_reqs = db.query(req_models.Requisition).filter(
        req_models.Requisition.status == "TENDER_OPEN"
    ).order_by(req_models.Requisition.id.desc()).all()
    result = []
    for req in open_reqs:
        staff = db.query(user_models.User).filter(user_models.User.id == req.staff_id).first()
        item_rows = []
        for request_item in _legacy_items(db, req):
            if request_item.status != "TENDER_OPEN":
                continue
            quote_lines = db.query(models.SupplierQuotationLine).filter(
                models.SupplierQuotationLine.requisition_item_id == request_item.id
            ).all()
            compliant = [line for line in quote_lines if line.is_compliant is True]
            lowest = min((line.total_price for line in compliant), default=None)
            lowest_id = next(
                (line.id for line in compliant if line.total_price == lowest), None
            )
            item_rows.append(_comparative_item(db, request_item, quote_lines, lowest_id))
        result.append({
            "requisition_id": req.id,
            "staff_id": req.staff_id,
            "staff_name": staff.full_name if staff else "",
            "created_at": req.created_at,
            "items": item_rows,
        })
    return result


@router.get(
    "/requisition/{req_id}/ai-matrix",
    response_model=List[schemas.ComparativeItemResponse],
)
def generate_ai_comparative_matrix(
    req_id: int,
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    req = db.query(req_models.Requisition).filter(req_models.Requisition.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.status not in {"PENDING_ADMIN", "TENDER_OPEN"}:
        raise HTTPException(status_code=400, detail="Comparisons are available after Head approval and quote submission")

    result = []
    for request_item in _legacy_items(db, req):
        item = db.query(inv_models.InventoryItem).filter(
            inv_models.InventoryItem.id == request_item.item_id
        ).first()
        quote_lines = db.query(models.SupplierQuotationLine).filter(
            models.SupplierQuotationLine.requisition_item_id == request_item.id
        ).all()
        if item and quote_lines:
            ai_engine.evaluate_quotations(item.item_name, quote_lines)
        compliant = [line for line in quote_lines if line.is_compliant is True]
        lowest = min((line.total_price for line in compliant), default=None)
        lowest_id = next(
            (line.id for line in compliant if line.total_price == lowest), None
        )
        result.append(_comparative_item(db, request_item, quote_lines, lowest_id))
    req.comparison_generated_at = datetime.datetime.utcnow()
    db.commit()
    return result
