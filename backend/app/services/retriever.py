"""
Hybrid retriever: combines knowledge-graph hits with vector similarity hits.

Returns deduplicated Documents ordered roughly by relevance: graph hits first
(usually more precise for symptom→condition reasoning), then vector hits.
"""
# Read 2026-06-17 — understand: 25%
from __future__ import annotations
from dataclasses import dataclass

from langchain_core.documents import Document

from backend.app.config import GRAPH_HOPS, GRAPH_MAX_NEIGHBOURS, VECTOR_K
from backend.app.services.entity_extractor import extract_from_question
from backend.app.services.graph_store import (
    chunk_ids_for_nodes,
    fuzzy_match_entity,
    load_graph,
    neighbours_within,
)
from backend.app.services.vector_store import fetch_chunks_by_id, load_vector_store


@dataclass
class RetrievalResult:
    docs: list[Document]
    matched_entities: list[str]       # graph nodes matched from the question
    candidate_conditions: list[str]   # Condition nodes reached via traversal
    vector_hits: int
    graph_hits: int


class HybridRetriever:
    def __init__(self) -> None:
        self.graph = load_graph()
        self.vs = load_vector_store()

    def retrieve(self, question: str) -> RetrievalResult:
        # --- graph side ----------------------------------------------------
        question_entities = extract_from_question(question)
        seeds: list[str] = []
        for q_ent in question_entities:
            seeds.extend(fuzzy_match_entity(self.graph, q_ent))
        seeds = list(dict.fromkeys(seeds))  # de-dupe, keep order

        expanded = neighbours_within(
            self.graph, seeds, hops=GRAPH_HOPS, max_neighbours=GRAPH_MAX_NEIGHBOURS
        )
        all_nodes = expanded | set(seeds)

        # Pull Condition nodes specifically — these are what the user actually
        # cares about ("what could it be?"). Used in the answer prompt and
        # surfaced in the API response for eval.
        candidate_conditions = [
            self.graph.nodes[n].get("display_name", n)
            for n in all_nodes
            if self.graph.nodes[n].get("type") == "Condition"
        ]

        graph_chunk_ids = chunk_ids_for_nodes(self.graph, all_nodes)
        graph_docs = fetch_chunks_by_id(self.vs, graph_chunk_ids[:GRAPH_MAX_NEIGHBOURS])

        # --- vector side ---------------------------------------------------
        vector_docs = self.vs.similarity_search(question, k=VECTOR_K)

        # --- merge & dedupe (by chunk_id, fall back to content hash) -------
        seen: set[str] = set()
        merged: list[Document] = []
        for d in graph_docs + vector_docs:
            key = d.metadata.get("chunk_id") or d.page_content[:80]
            if key in seen:
                continue
            seen.add(key)
            merged.append(d)

        return RetrievalResult(
            docs=merged,
            matched_entities=seeds,
            candidate_conditions=candidate_conditions,
            vector_hits=len(vector_docs),
            graph_hits=len(graph_docs),
        )


# Module-level singleton so the graph/Chroma load once.
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
