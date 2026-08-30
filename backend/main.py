import os
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
# Also load backend/.env if present
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import engine, Base, get_db
import models
import auth
import chat
import rag_storage
import rag_routes

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CogniStack API",
    description="Full-stack CogniStack Agentic RAG & AI Platform backend",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://think-forge-one.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(rag_storage.router)
app.include_router(rag_routes.router)

@app.get("/")
def read_root():
    return {"message": "CogniStack API is running."}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
