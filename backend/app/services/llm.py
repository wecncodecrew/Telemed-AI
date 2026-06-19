"""Chat LLM wrapper. Single source of truth for which chat model we use."""
# Read 2026-06-16 — understand: 100%
from langchain_ollama import ChatOllama

from backend.app.config import LLM_MODEL, OLLAMA_BASE_URL


def get_llm(temperature: float = 0.2) -> ChatOllama:
    """
    temperature=0.0 → use for extraction (we want deterministic JSON).
    temperature=0.2 → use for the triage answer (slightly more natural language).
    """
    return ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
    )
