import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import shutil
from typing import List, Tuple
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LCDocument
import google.generativeai as genai

from database import SessionLocal
import models

def get_faiss_directory(user_id: int, rag_app_id: int) -> str:
    base_dir = os.getenv("STORAGE_DIR", "storage")
    path = os.path.join(base_dir, "users", str(user_id), "rag_apps", str(rag_app_id), "faiss")
    os.makedirs(path, exist_ok=True)
    return path

# Embeddings Class Selector
def get_embeddings():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to load GoogleGenerativeAIEmbeddings ({e}). Using HuggingFace fallback.")
    
    # Fallback to local HuggingFace or deterministic embeddings
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Warning: HuggingFace fallback unavailable ({e}). Using Deterministic Fallback Embeddings.")
        from langchain_community.embeddings import FakeEmbeddings
        return FakeEmbeddings(size=384)

# Load file into LangChain Documents
def load_document_to_lc(file_path: str, file_type: str) -> List[LCDocument]:
    file_type = file_type.lower().replace(".", "")
    try:
        if file_type == "pdf":
            loader = PyPDFLoader(file_path)
            return loader.load()
        elif file_type == "txt":
            loader = TextLoader(file_path, encoding="utf-8")
            return loader.load()
        elif file_type == "docx":
            loader = Docx2txtLoader(file_path)
            return loader.load()
        elif file_type == "csv":
            loader = CSVLoader(file_path)
            return loader.load()
        else:
            print(f"Unsupported file type for LangChain: {file_type}")
            return []
    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
        return []

# Build and Persist FAISS Index
def build_and_save_faiss_index(user_id: int, rag_app_id: int) -> Tuple[bool, str]:
    db = SessionLocal()
    try:
        docs_metadata = db.query(models.Document).filter(
            models.Document.rag_app_id == rag_app_id,
            models.Document.user_id == user_id
        ).all()

        if not docs_metadata:
            return False, "No uploaded documents found for this RAG application."

        all_lc_docs = []
        for doc_meta in docs_metadata:
            if os.path.exists(doc_meta.file_path):
                lc_docs = load_document_to_lc(doc_meta.file_path, doc_meta.file_type)
                for d in lc_docs:
                    d.metadata["source_filename"] = doc_meta.filename
                all_lc_docs.extend(lc_docs)

        if not all_lc_docs:
            return False, "Failed to extract text from documents."

        # Text Splitting
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(all_lc_docs)

        if not chunks:
            return False, "No chunks created after splitting."

        # Embeddings & FAISS
        embeddings = get_embeddings()
        vector_store = FAISS.from_documents(chunks, embeddings)

        faiss_dir = get_faiss_directory(user_id, rag_app_id)
        vector_store.save_local(faiss_dir)
        return True, f"Successfully indexed {len(chunks)} chunks across {len(docs_metadata)} documents."
    except Exception as e:
        return False, f"Failed to build FAISS index: {str(e)}"
    finally:
        db.close()

# Document Knowledge Search & Synthesis
def query_rag_application(user_id: int, rag_app_id: int, question: str, chat_history: list = None) -> dict:
    faiss_dir = get_faiss_directory(user_id, rag_app_id)
    index_file = os.path.join(faiss_dir, "index.faiss")
    
    if not os.path.exists(index_file):
        return {
            "answer": "Documents have not been processed yet. Please click 'Process Documents' to enable document search.",
            "sources": []
        }

    try:
        embeddings = get_embeddings()
        vector_store = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
        retrieved_docs = vector_store.similarity_search(question, k=4)

        if not retrieved_docs:
            return {
                "answer": "No relevant information found in your uploaded documents for this question.",
                "sources": []
            }

        # Build Context String
        context_parts = []
        sources = []
        for i, doc in enumerate(retrieved_docs, 1):
            src_name = doc.metadata.get("source_filename", "Document")
            context_parts.append(f"[{src_name}]\n{doc.page_content}")
            if src_name not in sources:
                sources.append(src_name)

        context_str = "\n\n".join(context_parts)

        # Prompt Synthesis
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            answer = f"Based on your documents ({', '.join(sources)}):\n\n{context_str[:300]}..."
            return {"answer": answer, "sources": sources}

        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel("gemini-3.6-flash")
        except Exception:
            try:
                model = genai.GenerativeModel("gemini-flash-latest")
            except Exception:
                model = genai.GenerativeModel("gemini-pro-latest")

        recent_context = ""
        if chat_history:
            recent_turns = [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in chat_history[-4:]]
            recent_context = "PREVIOUS CONVERSATION:\n" + "\n".join(recent_turns) + "\n\n"

        prompt = f"""You are a helpful AI assistant answering questions using information from the user's uploaded documents.

{recent_context}DOCUMENT CONTEXT:
{context_str}

USER QUESTION:
{question}

Instructions: Provide a clear, natural, and helpful response based on the provided document context. Cite source document names naturally where relevant. Do not include technical system tags.
"""
        response = model.generate_content(prompt)
        return {"answer": response.text, "sources": sources}
    except Exception as e:
        return {"answer": f"Unable to retrieve an answer at this time. Please try again.", "sources": []}

