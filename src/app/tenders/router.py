from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.app.database import get_db
from src.app.tenders import models, schemas, ai_engine
from src.app.requisitions import models as req_models
from src.app.inventory import models as inv_models

router = APIRouter(prefix="/tenders", tags=["Supplier Tenders & AI Comparison"])

@router.post("/quotations", response_model=schemas.QuotationResponse)
def submit_supplier_quotation(quote: schemas.QuotationCreate, db: Session = Depends(get_db)):
    req = db.query(req_models.Requisition).filter(req_models.Requisition.id == quote.requisition_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if req.status != "TENDER_OPEN":
        raise HTTPException(status_code=400, detail="This requisition is not open for supplier tendering")

    new_quote = models.SupplierQuotation(**quote.model_dump())
    db.add(new_quote)
    db.commit()
    db.refresh(new_quote)
    return new_quote

@router.get("/requisition/{req_id}/ai-matrix", response_model=List[schemas.QuotationResponse])
def generate_ai_comparative_matrix(req_id: int, db: Session = Depends(get_db)):
    req = db.query(req_models.Requisition).filter(req_models.Requisition.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")

    item = db.query(inv_models.InventoryItem).filter(inv_models.InventoryItem.id == req.item_id).first()
    quotes = db.query(models.SupplierQuotation).filter(models.SupplierQuotation.requisition_id == req_id).all()

    ranked_quotes = ai_engine.evaluate_quotations(item.item_name, quotes)
    db.commit()
    return ranked_quotes
