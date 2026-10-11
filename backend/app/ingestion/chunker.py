"""
Turn cleaned MedlinePlus records into chunked LangChain Documents.

Every chunk gets a stable `chunk_id` so we can:
  - look it up later from Chroma by id, and
  - reference it from graph nodes (a node "knows" which chunks mention it).
"""
# Read 2026-06-18 — understand: 50%
from __future__ import annotations
import hashlib
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.config import CHUNK_OVERLAP, CHUNK_SIZE


def _chunk_id(title: str, idx: int, content: str) -> str:
    h = hashlib.sha1(f"{title}|{idx}|{content[:80]}".encode("utf-8")).hexdigest()[:16]
    return f"{h}"


def records_to_documents(records: Iterable[dict]) -> list[Document]:
    docs: list[Document] = []
    for rec in records:
        aka = ", ".join(rec.get("also_called", []))
        header = f"# {rec['title']}\n"
        if aka:
            header += f"Also known as: {aka}\n"
        docs.append(
            Document(
                page_content=header + "\n" + rec["text"],
                metadata={"title": rec["title"], "url": rec.get("url", "")},
            )
        )
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    # Attach stable chunk_id to every chunk.
    per_title_idx: dict[str, int] = {}
    for c in chunks:
        title = c.metadata.get("title", "Untitled")
        idx = per_title_idx.get(title, 0)
        per_title_idx[title] = idx + 1
        c.metadata["chunk_id"] = _chunk_id(title, idx, c.page_content)
    return chunks
