# CogniStack - Agentic RAG & AI Chatbot Platform

A ChatGPT-style full-stack AI chatbot platform built with React, Tailwind CSS, FastAPI, PostgreSQL, LangChain, LangGraph, FAISS, Gemini AI, DuckDuckGo Web Search, and LangSmith.

## Tech Stack
- **Frontend**: React + Tailwind CSS + Axios
- **Backend**: FastAPI + Python
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **Auth**: JWT + bcrypt
- **AI / Workflows**: Gemini API, LangChain, LangGraph, FAISS Vector DB, DuckDuckGo Search
- **Observability**: LangSmith
- **Deployment**: Docker & Docker Compose

## Quick Start (Phase 1)

1. Start PostgreSQL with Docker:
   ```bash
   docker compose up -d
   ```

2. Setup Backend:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. Setup Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
