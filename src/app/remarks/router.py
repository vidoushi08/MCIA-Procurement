from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.app.database import get_db
from src.app.remarks import models, schemas
from src.app.security import require_roles
from src.app.users import models as user_models

router = APIRouter(prefix="/remarks", tags=["Staff Remarks"])

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_REMARK = 5
ALLOWED_TYPES = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG"),
}


def to_response(db: Session, remarks: List[models.Remark]) -> List[schemas.RemarkResponse]:
    names = {u.id: u.full_name for u in db.query(user_models.User).all()}
    ids = [r.id for r in remarks]
    attachments = {}
    if ids:
        rows = (
            db.query(models.RemarkAttachment.id, models.RemarkAttachment.remark_id, models.RemarkAttachment.filename,
                     models.RemarkAttachment.content_type, models.RemarkAttachment.size)
            .filter(models.RemarkAttachment.remark_id.in_(ids))
            .order_by(models.RemarkAttachment.id)
            .all()
        )
        for row in rows:
            attachments.setdefault(row.remark_id, []).append(
                schemas.AttachmentInfo(id=row.id, filename=row.filename, content_type=row.content_type, size=row.size)
            )
    return [
        schemas.RemarkResponse.model_validate(r).model_copy(
            update={"staff_name": names.get(r.staff_id), "attachments": attachments.get(r.id, [])}
        )
        for r in remarks
    ]


@router.post("/", response_model=schemas.RemarkResponse)
def submit_remark(
    body: schemas.RemarkCreate,
    db: Session = Depends(get_db),
    staff: user_models.User = Depends(require_roles("STAFF")),
):
    remark = models.Remark(staff_id=staff.id, **body.model_dump())
    db.add(remark)
    db.commit()
    db.refresh(remark)
    return to_response(db, [remark])[0]


@router.get("/mine", response_model=List[schemas.RemarkResponse])
def my_remarks(
    db: Session = Depends(get_db),
    staff: user_models.User = Depends(require_roles("STAFF")),
):
    remarks = db.query(models.Remark).filter(models.Remark.staff_id == staff.id).order_by(models.Remark.id.desc()).all()
    return to_response(db, remarks)


@router.get("/", response_model=List[schemas.RemarkResponse])
def all_remarks(
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    remarks = db.query(models.Remark).order_by(models.Remark.id.desc()).all()
    return to_response(db, remarks)


@router.put("/{remark_id}/status", response_model=schemas.RemarkResponse)
def update_remark_status(
    remark_id: int,
    body: schemas.RemarkStatusUpdate,
    db: Session = Depends(get_db),
    _admin: user_models.User = Depends(require_roles("ADMIN")),
):
    remark = db.query(models.Remark).filter(models.Remark.id == remark_id).first()
    if not remark:
        raise HTTPException(status_code=404, detail="Remark not found")
    if body.status not in schemas.REMARK_STATUSES:
        raise HTTPException(status_code=400, detail="Status must be PENDING_REVIEW, IN_PROGRESS or RESOLVED")
    remark.status = body.status
    if body.admin_response is not None:
        remark.admin_response = body.admin_response.strip() or None
    db.commit()
    db.refresh(remark)
    return to_response(db, [remark])[0]


@router.post("/{remark_id}/attachments", response_model=schemas.RemarkResponse)
def upload_attachments(
    remark_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    staff: user_models.User = Depends(require_roles("STAFF")),
):
    remark = db.query(models.Remark).filter(models.Remark.id == remark_id, models.Remark.staff_id == staff.id).first()
    if not remark:
        raise HTTPException(status_code=404, detail="Remark not found")
    existing = db.query(models.RemarkAttachment).filter(models.RemarkAttachment.remark_id == remark.id).count()
    if existing + len(files) > MAX_ATTACHMENTS_PER_REMARK:
        raise HTTPException(status_code=400, detail=f"A remark can have at most {MAX_ATTACHMENTS_PER_REMARK} attachments")

    prepared = []
    for upload in files:
        name = (upload.filename or "").strip()
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"{name or 'File'} must be a PDF, JPG or PNG")
        content_type, magic = ALLOWED_TYPES[ext]
        data = upload.file.read(MAX_ATTACHMENT_BYTES + 1)
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status_code=400, detail=f"{name} is larger than 10 MB")
        if not data.startswith(magic):
            raise HTTPException(status_code=400, detail=f"{name} is not a valid {ext[1:].upper()} file")
        prepared.append(models.RemarkAttachment(
            remark_id=remark.id, filename=name[:255], content_type=content_type, size=len(data), data=data,
        ))

    db.add_all(prepared)
    db.commit()
    db.refresh(remark)
    return to_response(db, [remark])[0]


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: user_models.User = Depends(require_roles("STAFF", "ADMIN")),
):
    attachment = db.query(models.RemarkAttachment).filter(models.RemarkAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    remark = db.query(models.Remark).filter(models.Remark.id == attachment.remark_id).first()
    if user.role == "STAFF" and remark.staff_id != user.id:
        raise HTTPException(status_code=403, detail="You can only open your own attachments")
    safe_name = attachment.filename.replace('"', "")
    return Response(
        content=attachment.data,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )
