"""
The end-to-end GraphRAG pipeline.

answer(question) -> {
    "answer":   str,
    "sources":  [{"title": ..., "url": ...}, ...],
    "entities": [str, ...]   # graph entities matched in the question
}
"""
# Read 2026-06-12 — understand: 20%
from __future__ import annotations
from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from backend.app.services.llm import get_llm
from backend.app.services.prompts import get_triage_prompt
from backend.app.services.retriever import get_retriever


class RagResult(TypedDict):
    answer: str
    sources: list[dict]
    entities: list[str]
    candidate_conditions: list[str]


def _format_docs(docs: list[Document]) -> str:
    if not docs:
        return "(no relevant context found)"
    parts = []
    for i, d in enumerate(docs, 1):
        title = d.metadata.get("title", "Untitled")
        parts.append(f"[{i}] {title}\n{d.page_content}")
    return "\n\n---\n\n".join(parts)


def _dedupe_sources(docs: list[Document]) -> list[dict]:
    seen, out = set(), []
    for d in docs:
        title = d.metadata.get("title", "")
        if title and title not in seen:
            seen.add(title)
            out.append({"title": title, "url": d.metadata.get("url", "")})
    return out


def answer(question: str) -> RagResult:
    retriever = get_retriever()
    result = retriever.retrieve(question)

    prompt = get_triage_prompt()
    llm = get_llm(temperature=0.2)
    chain = prompt | llm | StrOutputParser()

    text = chain.invoke(
        {
            "context": _format_docs(result.docs),
            "entities": ", ".join(result.matched_entities) or "(none)",
            "candidate_conditions": ", ".join(result.candidate_conditions) or "(none)",
            "question": question,
        }
    )

    return {
        "answer": text,
        "sources": _dedupe_sources(result.docs),
        "entities": result.matched_entities,
        "candidate_conditions": result.candidate_conditions,
    }


def warmup() -> None:
    """Pre-load the retriever and ping the LLM so the first /chat is fast."""
    try:
        get_retriever()
    except FileNotFoundError:
        # Graph not built yet — that's OK; /health will report it.
        return
    try:
        get_llm().invoke("ok")
    except Exception:
        pass


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "I have a sore throat and mild fever for two days. What could it be?"
    res = answer(q)
    print("\n=== ANSWER ===\n")
    print(res["answer"])
    print("\n=== SYMPTOMS MATCHED ===")
    print(res["entities"])
    print("\n=== CANDIDATE CONDITIONS (from graph) ===")
    print(res["candidate_conditions"])
    print("\n=== SOURCES ===")
    for s in res["sources"]:
        print(f"- {s['title']}  {s['url']}")
