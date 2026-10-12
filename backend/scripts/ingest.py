"""
One-time ingestion pipeline:
    1. Parse MedlinePlus XML -> clean JSONL
    2. Chunk -> Documents
    3. Embed -> Chroma vector store
    4. LLM-extract entities/relations -> NetworkX graph

Run from the project root, with the backend venv active:
    python -m backend.scripts.ingest                # full run
    python -m backend.scripts.ingest --limit 50     # quick smoke test
    python -m backend.scripts.ingest --skip-graph   # data + vectors only
"""
from __future__ import annotations
import argparse

from backend.app.ingestion.chunker import chunk_documents, records_to_documents
from backend.app.ingestion.data_loader import load_records
from backend.app.ingestion.graph_builder import build_graph_from_chunks
from backend.app.services.vector_store import build_vector_store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Only ingest N chunks (debugging)")
    ap.add_argument("--skip-graph", action="store_true", help="Skip the slow graph build step")
    ap.add_argument("--skip-vectors", action="store_true", help="Skip the vector store build step")
    args = ap.parse_args()

    print("Step 1/4: loading clean MedlinePlus records ...")
    records = load_records()
    print(f"  loaded {len(records)} topics")
    if not records:
        print("  ⚠  No records found — the MedlinePlus XML may be empty or missing.")
        print("  Fallback will be used at query time.")
        return

    print("Step 2/4: chunking ...")
    docs = records_to_documents(records)
    chunks = chunk_documents(docs)
    print(f"  produced {len(chunks)} chunks from {len(docs)} documents")

    target_chunks = chunks[: args.limit] if args.limit else chunks

    if not args.skip_vectors:
        print("Step 3/4: embedding + writing to Chroma ...")
        build_vector_store(target_chunks)
    else:
        print("Step 3/4: SKIPPED (--skip-vectors)")

    if not args.skip_graph:
        print("Step 4/4: building knowledge graph (slow — ~1 LLM call per chunk) ...")
        build_graph_from_chunks(target_chunks)
    else:
        print("Step 4/4: SKIPPED (--skip-graph)")

    print("\nDone. Next:")
    print("  uvicorn backend.app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
