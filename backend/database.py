import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Render/Supabase PostgreSQL URLs often start with postgres://, SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Handle SQLite paths and thread settings
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # If the URL is sqlite:///./backend/sql_app.db but backend/ folder doesn't exist in current cwd
    if "/./backend/" in DATABASE_URL and not os.path.exists("backend"):
        DATABASE_URL = DATABASE_URL.replace("/./backend/", "/./")
    elif "backend/" in DATABASE_URL and not os.path.exists("backend"):
        DATABASE_URL = DATABASE_URL.replace("backend/", "")

print(f"Connecting to database at {DATABASE_URL.split('@')[-1]}...")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()