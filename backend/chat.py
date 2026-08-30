import os
import json
import asyncio
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, SessionLocal
import models
from auth import get_current_user
from workflow import run_agent_workflow

router = APIRouter(prefix="/api/chats", tags=["chats"])

# Pydantic Schemas
class ChatCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ChatUpdate(BaseModel):
    title: str

class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Router Endpoints
@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(chat_data: ChatCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = models.Chat(
        user_id=current_user.id,
        title=chat_data.title or "New Chat"
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.get("", response_model=List[ChatResponse])
def get_chats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = db.query(models.Chat).filter(
        models.Chat.user_id == current_user.id
    ).order_by(models.Chat.updated_at.desc()).all()
    return chats

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.patch("/{chat_id}", response_model=ChatResponse)
def update_chat(chat_id: int, chat_data: ChatUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    chat.title = chat_data.title
    chat.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(chat)
    return chat

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()
    return None

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def get_messages(chat_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = db.query(models.Message).filter(
        models.Message.chat_id == chat_id
    ).order_by(models.Message.created_at.asc()).all()
    return messages

@router.post("/{chat_id}/messages", response_model=MessageResponse)
def send_message(chat_id: int, msg_data: MessageCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 1. Fetch prior conversation history from database
    prior_messages = db.query(models.Message).filter(
        models.Message.chat_id == chat_id
    ).order_by(models.Message.created_at.asc()).all()
    chat_history = [{"role": m.role, "content": m.content} for m in prior_messages]

    # 2. Save incoming user message
    user_msg = models.Message(
        chat_id=chat_id,
        role="user",
        content=msg_data.content
    )
    db.add(user_msg)
    db.commit()
    
    existing_msg_count = len(prior_messages)
    if existing_msg_count == 0 or chat.title == "New Chat":
        chat.title = msg_data.content[:30] + ("..." if len(msg_data.content) > 30 else "")

    # 3. Execute LangGraph Agent Workflow with full chat history
    agent_res = run_agent_workflow(
        msg_data.content,
        user_id=current_user.id,
        chat_history=chat_history
    )
    ai_content = agent_res["answer"]

    assistant_msg = models.Message(
        chat_id=chat_id,
        role="assistant",
        content=ai_content
    )
    db.add(assistant_msg)
    
    chat.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg

# STREAMING ENDPOINT WITH CONVERSATION MEMORY & LANGGRAPH WORKFLOW
@router.post("/{chat_id}/messages/stream")
def stream_message(chat_id: int, msg_data: MessageCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # 1. Fetch prior conversation history from database
    prior_messages = db.query(models.Message).filter(
        models.Message.chat_id == chat_id
    ).order_by(models.Message.created_at.asc()).all()
    chat_history = [{"role": m.role, "content": m.content} for m in prior_messages]

    # 2. Save incoming user message
    user_msg = models.Message(
        chat_id=chat_id,
        role="user",
        content=msg_data.content
    )
    db.add(user_msg)
    db.commit()
    
    existing_msg_count = len(prior_messages)
    if existing_msg_count == 0 or chat.title == "New Chat":
        chat.title = msg_data.content[:30] + ("..." if len(msg_data.content) > 30 else "")
        db.commit()

    def generate_sse():
        # Execute LangGraph Workflow with full conversational history
        agent_res = run_agent_workflow(
            msg_data.content,
            user_id=current_user.id,
            chat_history=chat_history
        )
        full_text = agent_res["answer"]

        # Stream chunks progressively to client
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"chunk": chunk, "route": agent_res["route"]})
            yield f"data: {payload}\n\n"

        # Save completed assistant message to DB
        db_stream = SessionLocal()
        try:
            assistant_msg = models.Message(
                chat_id=chat_id,
                role="assistant",
                content=full_text
            )
            db_stream.add(assistant_msg)
            
            chat_obj = db_stream.query(models.Chat).filter(models.Chat.id == chat_id).first()
            if chat_obj:
                chat_obj.updated_at = datetime.datetime.utcnow()
            
            db_stream.commit()
            db_stream.refresh(assistant_msg)
            
            done_payload = json.dumps({
                "done": True,
                "message_id": assistant_msg.id,
                "content": full_text,
                "route": agent_res["route"],
                "sources": agent_res.get("sources", [])
            })
            yield f"data: {done_payload}\n\n"
        finally:
            db_stream.close()

    return StreamingResponse(generate_sse(), media_type="text/event-stream")

