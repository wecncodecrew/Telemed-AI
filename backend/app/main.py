"""FastAPI entrypoint. Run with: uvicorn backend.app.main:app --reload --port 8000"""
# Read 2026-06-15 — understand: 75%
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.config import ALLOWED_ORIGINS
from backend.app.services.graph_rag import warmup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up: load the graph + vector store + ping the LLM once.
    # This makes the first /chat call fast instead of ~30s.
    warmup()
    yield


app = FastAPI(
    title="Telemed Chatbot API",
    description=(
        "GraphRAG-powered symptom chatbot. Given symptoms, returns possible "
        "conditions, typical care, red flags, and MedlinePlus sources. "
        "Student learning project — not for clinical use."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
