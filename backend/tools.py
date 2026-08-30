from typing import List, Dict, Any
from ddgs import DDGS

def duckduckgo_search_tool(query: str, max_results: int = 4) -> Dict[str, Any]:
    """
    Perform a live web search using DuckDuckGo.
    Returns a dictionary containing 'results_text' and 'sources'.
    """
    try:
        results = []
        sources = []
        
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for i, res in enumerate(raw_results, 1):
                title = res.get("title", "Search Result")
                snippet = res.get("body", "")
                url = res.get("href", "")
                
                results.append(f"[Web Source {i}: {title}] ({url})\n{snippet}")
                sources.append({"title": title, "url": url})
        
        results_text = "\n\n".join(results) if results else "No web results found."
        return {
            "results_text": results_text,
            "sources": sources
        }
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return {
            "results_text": f"Web search could not be completed: {str(e)}",
            "sources": []
        }
