"""Documents: contracts / templates / legal / compliance."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import DocumentEntry
from database import get_db
from models.db_models import Document, DocumentCategory

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=List[DocumentEntry])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.post("", response_model=DocumentEntry)
def add_document(payload: DocumentEntry, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"id"})
    data["category"] = DocumentCategory(data["category"])
    item = Document(**data)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    item = db.query(Document).filter(Document.id == document_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(item); db.commit()
    return {"status": "deleted", "id": document_id}


@router.get("/by-category/{category}", response_model=List[DocumentEntry])
def by_category(category: str, db: Session = Depends(get_db)):
    cat = DocumentCategory(category)
    return db.query(Document).filter(Document.category == cat).all()
