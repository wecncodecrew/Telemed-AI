# I read this on 2026-06-21 and understand it.
"""Central configuration. Import this — never hard-code settings elsewhere."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"
GRAPH_DIR = DATA_DIR / "graph"
GRAPH_PICKLE = GRAPH_DIR / "kg.pickle"
CLEAN_JSONL = DATA_DIR / "medlineplus_clean.jsonl"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

VECTOR_K = int(os.getenv("VECTOR_K", "4"))
GRAPH_HOPS = int(os.getenv("GRAPH_HOPS", "2"))
GRAPH_MAX_NEIGHBOURS = int(os.getenv("GRAPH_MAX_NEIGHBOURS", "20"))

COLLECTION_NAME = "medlineplus"

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
    if o.strip()
]

NODE_TYPES = ("Condition", "Symptom", "BodyPart", "Treatment", "RiskFactor", "Medication")
EDGE_TYPES = ("HAS_SYMPTOM", "AFFECTS", "TREATED_BY", "INCREASES_RISK_OF", "LOCATED_IN")

for d in (DATA_DIR, RAW_DIR, CHROMA_DIR, GRAPH_DIR):
    d.mkdir(parents=True, exist_ok=True)
