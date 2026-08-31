import os
import shutil
import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["file-storage"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit

# Pydantic Schemas
class DocumentResponse(BaseModel):
    id: int
    user_id: int
    rag_app_id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Storage helper function
def get_user_storage_path(user_id: int, rag_app_id: int) -> str:
    base_dir = os.getenv("STORAGE_DIR", "storage")
    path = os.path.join(base_dir, "users", str(user_id), "rag_apps", str(rag_app_id), "documents")
    os.makedirs(path, exist_ok=True)
    return path

# Upload Document Endpoint
@router.post("/rag-apps/{rag_app_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    rag_app_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify RAG Application ownership
    rag_app = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == rag_app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not rag_app:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    # 2. Validate File Extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 3. Read and Validate File Size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds maximum 10MB limit")

    # 4. Save to Local Storage
    doc_folder = get_user_storage_path(current_user.id, rag_app_id)
    # Sanitize filename
    safe_filename = f"{int(datetime.datetime.utcnow().timestamp())}_{file.filename}"
    file_path = os.path.join(doc_folder, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # 5. Save Metadata in PostgreSQL
    doc_model = models.Document(
        user_id=current_user.id,
        rag_app_id=rag_app_id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_ext.replace(".", ""),
        file_size=file_size
    )
    db.add(doc_model)
    db.commit()
    db.refresh(doc_model)
    return doc_model

# List Documents Endpoint
@router.get("/rag-apps/{rag_app_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    rag_app_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rag_app = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == rag_app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not rag_app:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    docs = db.query(models.Document).filter(
        models.Document.rag_app_id == rag_app_id,
        models.Document.user_id == current_user.id
    ).all()
    return docs

# Delete Document Endpoint
@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete physical file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            print(f"Warning: Failed to delete physical file {doc.file_path}: {e}")

    # Remove database row
    db.delete(doc)
    db.commit()
    return None
