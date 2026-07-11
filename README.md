# Telemed Chatbot

A symptom chatbot built with **GraphRAG** on **MedlinePlus** health topics.
Describe symptoms → hybrid retrieval (knowledge graph + vector search) → local LLM via Ollama → possible conditions, typical care, red flags, sources.

> ⚠️ **Student learning project.** Always consult a doctor for real health concerns.

📖 **Read [GUIDE.md](./GUIDE.md) first.** That is your e-guide for the project — concepts, architecture, phased plan, mermaid diagrams.

## Quickstart

### 1. Model & Data Setup

Install [Ollama](https://ollama.com/) and pull the necessary local models:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Download the [MedlinePlus XML dataset](https://medlineplus.gov/xml.html) and place it in the `data/raw/` directory.

### 2. Backend Initialization (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Build the knowledge base (one-time, takes a while)
cd ..
python -m backend.scripts.ingest

# Start the backend API
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Initialization (Streamlit)

Open a **NEW terminal window**:

```bash
cd frontend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Start the interface
streamlit run app.py
```

Open <http://localhost:8501>. Backend docs at <http://localhost:8000/docs>.

## Repository layout

```
telemed-AI/
├── GUIDE.md           # ← start here
├── README.md
├── backend/           # FastAPI + GraphRAG service
│   ├── app/
│   │   ├── api/       # HTTP routes
│   │   ├── services/  # ML / retrieval logic
│   │   └── ingestion/ # one-time data pipeline
│   └── scripts/       # ingest.py
├── frontend/          # Streamlit UI
└── data/              # gitignored — raw XML, chroma, graph pickle
```

## Architecture

```
User → Streamlit (frontend, :8501)
         ↓ HTTP POST /chat
       FastAPI (backend, :8000)
         ↓
       GraphRAG service
         ├→ Entity extractor → Ollama
         ├→ NetworkX graph traversal
         ├→ Chroma vector search
         └→ Triage prompt → Ollama → answer + sources
```

See [GUIDE.md §7](./GUIDE.md#7-system-architecture) for the full mermaid diagram.

## Contributing

Open-source learning project. PRs welcome — open an issue first, branch off `main`, request a review.
