import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
import google.generativeai as genai

from tools import duckduckgo_search_tool
import rag_service

# 1. LangSmith Observability Setup (Environment Controlled)
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() in ("true", "1")
if LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if os.getenv("LANGSMITH_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    if os.getenv("LANGSMITH_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
    print(f"LangSmith Tracing ENABLED for project: {os.getenv('LANGSMITH_PROJECT', 'ai-chatbot')}")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# 2. Define LangGraph Workflow State
class GraphState(TypedDict):
    question: str
    chat_history: List[Dict[str, Any]]
    user_id: int
    rag_app_id: Optional[int]
    route: str
    context: str
    sources: List[Any]
    final_answer: str

# 3. Router Node (Decides Workflow Path)
def router_node(state: GraphState) -> GraphState:
    question = state["question"].lower()
    rag_app_id = state.get("rag_app_id")

    if rag_app_id:
        state["route"] = "rag"
        return state

    search_keywords = ["latest", "news", "current", "version", "weather", "today", "who won", "stock price", "release date"]
    if any(keyword in question for keyword in search_keywords):
        state["route"] = "web_search"
    else:
        state["route"] = "gemini"

    return state

# 4. Direct AI Chat Node (Multi-turn conversational memory)
def gemini_node(state: GraphState) -> GraphState:
    question = state["question"]
    chat_history = state.get("chat_history", [])
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        state["final_answer"] = f"Please configure your API key in the settings to enable live responses."
        state["sources"] = []
        return state

    try:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel("gemini-3.6-flash")
        except Exception:
            try:
                model = genai.GenerativeModel("gemini-flash-latest")
            except Exception:
                model = genai.GenerativeModel("gemini-pro-latest")

        # Build multi-turn conversational history
        contents = []
        for msg in chat_history[-10:]:  # Keep recent turns for rich context
            role = "user" if msg.get("role") == "user" else "model"
            text_content = msg.get("content", "").strip()
            if text_content:
                contents.append({"role": role, "parts": [text_content]})

        # Ensure the latest question is at the end
        if not contents or contents[-1]["parts"][0] != question:
            contents.append({"role": "user", "parts": [question]})

        response = model.generate_content(contents)
        state["final_answer"] = response.text
        state["sources"] = []
    except Exception as e:
        state["final_answer"] = f"An error occurred while generating the response. Please try again."
        state["sources"] = []
    return state

# 5. Document Knowledge Retrieval Node
def rag_node(state: GraphState) -> GraphState:
    user_id = state["user_id"]
    rag_app_id = state.get("rag_app_id")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    if not rag_app_id:
        state["final_answer"] = "No document collection selected."
        state["sources"] = []
        return state

    rag_result = rag_service.query_rag_application(user_id, rag_app_id, question, chat_history=chat_history)
    state["final_answer"] = rag_result["answer"]
    state["sources"] = rag_result.get("sources", [])
    return state

# 6. Web Search Node
def web_search_node(state: GraphState) -> GraphState:
    question = state["question"]
    chat_history = state.get("chat_history", [])
    search_res = duckduckgo_search_tool(question, max_results=4)
    results_text = search_res["results_text"]
    sources = search_res["sources"]

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        state["final_answer"] = f"Here is the information found:\n\n{results_text}"
        state["sources"] = sources
        return state

    try:
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

        prompt = f"""You are a helpful AI assistant. Answer the user's question using the real-time search results below.

{recent_context}USER QUESTION:
{question}

SEARCH RESULTS:
{results_text}

Instructions: Provide a clear, accurate, and comprehensive response. Cite source links naturally if relevant. Do not include technical system tags.
"""
        response = model.generate_content(prompt)
        state["final_answer"] = response.text
        state["sources"] = sources
    except Exception as e:
        state["final_answer"] = f"Here is the information found:\n\n{results_text}"
        state["sources"] = sources

    return state

# 7. Route Conditional Logic Function
def select_next_node(state: GraphState) -> str:
    return state["route"]

# 8. Build LangGraph Workflow Graph
workflow = StateGraph(GraphState)

workflow.add_node("router", router_node)
workflow.add_node("gemini", gemini_node)
workflow.add_node("rag", rag_node)
workflow.add_node("web_search", web_search_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    select_next_node,
    {
        "gemini": "gemini",
        "rag": "rag",
        "web_search": "web_search"
    }
)

workflow.add_edge("gemini", END)
workflow.add_edge("rag", END)
workflow.add_edge("web_search", END)

# Compile LangGraph Executable
langgraph_app = workflow.compile()

def run_agent_workflow(question: str, user_id: int, rag_app_id: Optional[int] = None, chat_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    initial_state: GraphState = {
        "question": question,
        "chat_history": chat_history or [],
        "user_id": user_id,
        "rag_app_id": rag_app_id,
        "route": "gemini",
        "context": "",
        "sources": [],
        "final_answer": ""
    }
    
    final_state = langgraph_app.invoke(initial_state)
    return {
        "answer": final_state["final_answer"],
        "route": final_state["route"],
        "sources": final_state.get("sources", [])
    }
