# 🩺 Telemed Chatbot (Wecncode Open Source)


A symptom chatbot built with **GraphRAG** on **MedlinePlus** health topics.
Describe symptoms => hybrid retrieval (knowledge graph + vector search) → local LLM via Ollama → possible conditions, typical care, red flags, sources.


The system utilizes hybrid retrieval (combining knowledge graphs with vector search) and routes data through local LLMs via Ollama to provide potential conditions, typical care instructions, red flags, and verified sources. 

> **⚠️ Disclaimer:** This is an open-source educational project. It is not a substitute for professional medical advice. Always consult a doctor for real health concerns.

📖 **Read [GUIDE.md](./GUIDE.md) first.** It is your comprehensive e-guide for the project, detailing core concepts, architecture, phased plans, and mermaid diagrams.


---

## 🌟 The Developer Ethos
We are building this project under the Wecncode community guidelines. Our development philosophy is:
* **Local First:** Zero cloud API keys. Everything runs securely on your machine.
* **Tech Stack Agnostic:** A decoupled architecture means you can use the backend API to build frontends in React, Vue, Vanilla JS, or whatever you prefer.
* **Beginner Friendly:** We prioritize highly readable, well-commented code.
* **Safety Conscious:** We build tools that provide disclaimers and verified sources, not medical diagnoses.

---

## 🏗️ Architecture Layout

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


The project features a decoupled architecture separating the AI/Data engine from the user interface. 

### Repository Layout

```text
telemed-AI/
├── GUIDE.md           # ← start here
├── README.md
├── backend/           # FastAPI + GraphRAG service
│   ├── app/
│   │   ├── api/       # Exposed API contracts
│   │   ├── services/  # ML / retrieval logic
│   │   └── ingestion/ # one-time data pipeline
│   └── scripts/       # ingest.py
├── frontend/          # Default Streamlit UI (React/Vanilla JS starters welcome!)
└── data/              # gitignored — raw XML, chroma, graph pickle
```

### System Architecture

```text
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

For the complete network traversal and data-flow mermaid diagram, see [GUIDE.md §7](./GUIDE.md#7-system-architecture).

---

## 🚀 Quickstart Guide

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
Backend documentation is available at <http://localhost:8000/docs>.

### 3. Frontend Initialization (Streamlit)
Open a new terminal window:
```bash
cd frontend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Start the interface
streamlit run app.py
```
Access the interface at <http://localhost:8501>.

---

## 🤝 Contributing & The Task Matrix

This is an open-source learning project. We welcome PRs from developers of all skill levels. Please open an issue first, branch off `main`, and request a review.

Looking for a place to start? Check our active Task Matrix:

| Category | Domain Modules | Frontend UI | Quality & Safety |
| :--- | :--- | :--- | :--- |
| 🌱 **Beginner** (No ML needed) | Collect symptom datasets. Add crisis links. | Design chat UI wireframes. | Add mandatory medical disclaimers. |
| 🛠️ **Intermediate** (API/React/RAG) | Build diet & nutrition RAG pipelines. | Connect custom frontends to the API. | Write backend unit tests. Add input sanitization. |
| 🚀 **Advanced** (Strong Coding) | Implement mental health safety filters. | Build multi-turn contextual memory interfaces. | Build harmful query filters and integration tests. |

**Profiles:** Beginners focus on documentation and basic UI. Intermediates tackle pipelines and frontend components. Advanced builders focus on integration testing and complex memory.
