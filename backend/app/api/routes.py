"""HTTP routes. Keep these thin — call into services/ for real work."""
# Read 2026-06-15 — understand: 65%
from __future__ import annotations
from fastapi import APIRouter, HTTPException

from backend.app.config import CHROMA_DIR, GRAPH_PICKLE, LLM_MODEL, EMBEDDING_MODEL
from backend.app.schemas import ChatRequest, ChatResponse, HealthResponse, Source
from backend.app.services.graph_rag import answer

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_model=LLM_MODEL,
        embedding_model=EMBEDDING_MODEL,
        graph_loaded=GRAPH_PICKLE.exists(),
        vector_store_loaded=any(CHROMA_DIR.iterdir()) if CHROMA_DIR.exists() else False,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = answer(req.message)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Knowledge base not built yet: {e}. Run `python -m backend.scripts.ingest`.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
        entities_found=result.get("entities", []),
        candidate_conditions=result.get("candidate_conditions", []),
    )
