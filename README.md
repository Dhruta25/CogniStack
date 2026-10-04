# CogniStack

A full-stack AI chatbot platform with multi-turn conversation memory, RAG (Retrieval-Augmented Generation) document intelligence, real-time web search, and streaming responses — built with React, FastAPI, LangGraph, FAISS, and Gemini AI.

## Features

- **Multi-turn AI Chat** — Conversational memory across sessions powered by Gemini AI
- **RAG Document Q&A** — Upload PDFs, DOCX, TXT, or CSV files; ask questions grounded in your documents using FAISS vector search
- **Live Web Search** — Auto-routes time-sensitive queries to DuckDuckGo and synthesizes results with Gemini
- **Streaming Responses** — Server-sent events (SSE) for real-time word-by-word output
- **JWT Authentication** — Secure signup/login with bcrypt password hashing
- **LangGraph Workflow** — Agentic router dispatches each query to the correct processing node (Gemini / RAG / Web Search)
- **LangSmith Observability** — Optional tracing toggle via environment variable

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Backend | FastAPI, Python 3.11 |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| Auth | JWT (python-jose) + bcrypt |
| AI & Workflow | Google Gemini API, LangGraph, LangChain |
| Vector Search | FAISS + Google Generative AI Embeddings |
| Web Search | DuckDuckGo Search |
| Observability | LangSmith (optional) |
| Deployment | Docker, Vercel (frontend), Render (backend) |

## Project Structure

```
CogniStack/
├── backend/
│   ├── main.py          # FastAPI app, CORS, router registration
│   ├── auth.py          # JWT auth, signup/login endpoints
│   ├── chat.py          # Chat & message CRUD, SSE streaming
│   ├── workflow.py      # LangGraph agent (router → gemini/rag/web_search)
│   ├── rag_routes.py    # RAG application CRUD + reindex + chat endpoints
│   ├── rag_service.py   # FAISS index build & query logic
│   ├── rag_storage.py   # Document upload/delete endpoints
│   ├── tools.py         # DuckDuckGo search tool
│   ├── models.py        # SQLAlchemy ORM models
│   ├── database.py      # DB engine + session factory
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── ChatPage.jsx      # Main chat interface with sidebar
│       │   ├── RAGAppsPage.jsx   # Document collections + Q&A panel
│       │   ├── Login.jsx
│       │   └── Signup.jsx
│       ├── context/
│       │   └── AuthContext.jsx   # Auth state, login/logout/signup
│       ├── components/
│       │   └── ProtectedRoute.jsx
│       ├── services/
│       │   └── api.js            # Axios client + all API call functions
│       └── App.jsx
└── .env
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Configure environment

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Required variables:

```env
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_jwt_secret_key
DATABASE_URL=sqlite:///./sql_app.db
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`. API docs available at `/docs`.

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `SECRET_KEY` | JWT signing secret | `dev_secret_key_change_in_production` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `1440` (24h) |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./sql_app.db` |
| `STORAGE_DIR` | File storage root | `storage` |
| `CORS_ORIGINS` | Extra allowed origins (comma-separated) | — |
| `LANGSMITH_TRACING` | Enable LangSmith tracing (`true`/`false`) | `false` |
| `LANGSMITH_API_KEY` | LangSmith API key | — |
| `LANGSMITH_PROJECT` | LangSmith project name | — |

## How the AI Workflow Works

Every incoming message passes through a **LangGraph state machine**:

```
User Message
     │
  [Router]
     ├─ rag_app_id present? ──► [RAG Node] → FAISS similarity search → Gemini synthesis
     ├─ time-sensitive query? ──► [Web Search Node] → DuckDuckGo → Gemini synthesis
     └─ default ──────────────► [Gemini Node] → multi-turn chat with history
```

## Deployment

The backend is deployable to **Render** or any Python host. Set `DATABASE_URL` to a PostgreSQL connection string in production (the code automatically rewrites `postgres://` to `postgresql://` for SQLAlchemy compatibility).

The frontend is deployable to **Vercel** — set `VITE_API_URL` to your backend URL.
