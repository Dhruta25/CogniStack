import os
import shutil
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
import models
from auth import get_current_user
import rag_service

router = APIRouter(prefix="/api/rag-apps", tags=["rag-applications"])

# Pydantic Schemas
class RAGAppCreate(BaseModel):
    name: str

class RAGAppUpdate(BaseModel):
    name: str

class RAGAppResponse(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class RAGChatRequest(BaseModel):
    question: str

class RAGChatResponse(BaseModel):
    answer: str
    sources: List[str]

# Create RAG Application
@router.post("", response_model=RAGAppResponse, status_code=status.HTTP_201_CREATED)
def create_rag_app(
    app_data: RAGAppCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rag_app = models.RAGApplication(
        user_id=current_user.id,
        name=app_data.name
    )
    db.add(rag_app)
    db.commit()
    db.refresh(rag_app)
    return rag_app

# List RAG Applications
@router.get("", response_model=List[RAGAppResponse])
def list_rag_apps(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    apps = db.query(models.RAGApplication).filter(
        models.RAGApplication.user_id == current_user.id
    ).order_by(models.RAGApplication.updated_at.desc()).all()
    return apps

# Get RAG Application
@router.get("/{app_id}", response_model=RAGAppResponse)
def get_rag_app(
    app_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_obj = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="RAG Application not found")
    return app_obj

# Rename RAG Application
@router.patch("/{app_id}", response_model=RAGAppResponse)
def rename_rag_app(
    app_id: int,
    app_data: RAGAppUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_obj = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    app_obj.name = app_data.name
    app_obj.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(app_obj)
    return app_obj

# Delete RAG Application
@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rag_app(
    app_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_obj = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    # Remove physical RAG folder
    base_dir = os.getenv("STORAGE_DIR", "storage")
    app_folder = os.path.join(base_dir, "users", str(current_user.id), "rag_apps", str(app_id))
    if os.path.exists(app_folder):
        try:
            shutil.rmtree(app_folder)
        except Exception as e:
            print(f"Warning: Failed to delete RAG app folder {app_folder}: {e}")

    db.delete(app_obj)
    db.commit()
    return None

# Build Vector Index Endpoint
@router.post("/{app_id}/reindex")
def reindex_rag_app(
    app_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_obj = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    success, message = rag_service.build_and_save_faiss_index(current_user.id, app_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    app_obj.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "ok", "message": message}

# RAG Chat Endpoint
@router.post("/{app_id}/chat", response_model=RAGChatResponse)
def chat_with_rag_app(
    app_id: int,
    request: RAGChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app_obj = db.query(models.RAGApplication).filter(
        models.RAGApplication.id == app_id,
        models.RAGApplication.user_id == current_user.id
    ).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="RAG Application not found")

    result = rag_service.query_rag_application(current_user.id, app_id, request.question)
    return result
