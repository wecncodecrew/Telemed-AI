"""
`# Read 2026-06-12 — understand: 60%`
Streamlit chat UI for TelemedBot.

Talks to the FastAPI backend over HTTP. Knows nothing about ML.

Run with:   streamlit run frontend/app.py
"""
from __future__ import annotations
import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))


# ---------------------------------------------------------------------------
# Backend client
# ---------------------------------------------------------------------------
def backend_health() -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def send_chat(message: str, history: list[dict]) -> dict:
    payload = {
        "message": message,
        "history": [{"role": m["role"], "content": m["content"]} for m in history],
    }
    r = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="TelemedBot (Student MVP)", page_icon="🩺")

with st.sidebar:
    st.title("🩺 TelemedBot")
    st.markdown(
        "Describe your symptoms and I'll look up possible conditions and "
        "typical care from **MedlinePlus** using a knowledge graph + a local LLM."
    )
    st.warning(
        "**Student learning project.** Always consult a doctor for real health concerns."
    )

    st.markdown("---")
    st.subheader("Backend status")
    health = backend_health()
    if health is None:
        st.warning(f"Cannot reach backend at {BACKEND_URL}")
    else:
        ok = health.get("graph_loaded") and health.get("vector_store_loaded")
        if ok:
            st.success(
                f"OK · LLM: `{health.get('llm_model')}` · "
                f"Embed: `{health.get('embedding_model')}`"
            )
        else:
            st.warning(
                "Backend is up but the knowledge base isn't built.\n\n"
                "Run: `python -m backend.scripts.ingest`"
            )

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []

st.title("How can I help today?")
st.caption(
    "Describe your symptoms in plain language. I'll suggest possible conditions, "
    "typical care from MedlinePlus, when to see a doctor — and cite my sources."
)


def render_message(m: dict) -> None:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            if m.get("entities_found"):
                st.caption("Symptoms recognised: " + ", ".join(m["entities_found"]))
            if m.get("candidate_conditions"):
                with st.expander("Candidate conditions from the knowledge graph"):
                    for c in m["candidate_conditions"]:
                        st.markdown(f"- {c}")
            if m.get("sources"):
                with st.expander("Sources"):
                    for s in m["sources"]:
                        if s.get("url"):
                            st.markdown(f"- [{s['title']}]({s['url']})")
                        else:
                            st.markdown(f"- {s['title']}")


for m in st.session_state.messages:
    render_message(m)

if user_input := st.chat_input("e.g. I have a sore throat and mild fever for two days."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    render_message(st.session_state.messages[-1])

    with st.chat_message("assistant"):
        with st.spinner("Thinking ..."):
            try:
                resp = send_chat(user_input, st.session_state.messages[:-1])
                reply = resp.get("answer", "")
                sources = resp.get("sources", [])
                entities = resp.get("entities_found", [])
                conditions = resp.get("candidate_conditions", [])
            except requests.HTTPError as e:
                reply = f"Backend error: `{e.response.status_code}` — {e.response.text}"
                sources, entities, conditions = [], [], []
            except requests.RequestException as e:
                reply = f"Couldn't reach the backend at `{BACKEND_URL}`. Is it running?\n\n{e}"
                sources, entities, conditions = [], [], []

        st.markdown(reply)
        if entities:
            st.caption("Symptoms recognised: " + ", ".join(entities))
        if conditions:
            with st.expander("Candidate conditions from the knowledge graph"):
                for c in conditions:
                    st.markdown(f"- {c}")
        if sources:
            with st.expander("Sources"):
                for s in sources:
                    if s.get("url"):
                        st.markdown(f"- [{s['title']}]({s['url']})")
                    else:
                        st.markdown(f"- {s['title']}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": reply,
            "sources": sources,
            "entities_found": entities,
            "candidate_conditions": conditions,
        }
    )
