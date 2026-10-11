"""
Walk every chunk, call the LLM to extract entities + relations, and build
a NetworkX knowledge graph.

This is the slowest step of ingestion (~1 LLM call per chunk). Expect
30-90 minutes for the full MedlinePlus corpus on a laptop. That's normal.

To iterate fast while developing, pass `limit=50` and inspect the result.
"""
# Read 2026-06-18 — understand: 50%
from __future__ import annotations
import networkx as nx
from langchain_core.documents import Document
from tqdm import tqdm

from backend.app.services.entity_extractor import extract_from_chunk
from backend.app.services.graph_store import (
    add_entity,
    add_relation,
    new_graph,
    normalise,
    save_graph,
)


def build_graph_from_chunks(
    chunks: list[Document], limit: int | None = None
) -> nx.MultiDiGraph:
    if limit is not None:
        chunks = chunks[:limit]

    g = new_graph()
    failed = 0

    for c in tqdm(chunks, desc="extracting", unit="chunk"):
        chunk_id = c.metadata.get("chunk_id", "")
        try:
            ext = extract_from_chunk(c.page_content)
        except Exception:
            failed += 1
            continue

        # Add entities first so we can validate relations against them.
        present: set[str] = set()
        for e in ext["entities"]:
            key = add_entity(g, e["name"], e["type"], chunk_id)
            if key:
                present.add(key)

        for r in ext["relations"]:
            src = normalise(r.get("source", ""))
            dst = normalise(r.get("target", ""))
            if src in present and dst in present:
                add_relation(g, src, r["relation"], dst, chunk_id)

    print(
        f"Graph built: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges. "
        f"Failed extractions: {failed}/{len(chunks)}."
    )
    save_graph(g)
    return g
