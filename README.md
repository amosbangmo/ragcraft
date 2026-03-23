
![Python](https://img.shields.io/badge/python-3.13-blue)
![Streamlit](https://img.shields.io/badge/streamlit-app-red)
![License](https://img.shields.io/badge/license-MIT-green)

# 📚 RAGCraft

> A portfolio-grade **Retrieval-Augmented Generation (RAG) platform** showcasing how modern document intelligence systems can be built with **multimodal ingestion, hybrid retrieval, query rewriting, reranking, inspectable pipelines, and comparative retrieval evaluation**.

RAGCraft is a **multi-user, multi-project RAG system** designed to go beyond simple chatbot demos and demonstrate how a more production-oriented document intelligence workflow can be implemented.

The platform supports **document ingestion, multimodal asset extraction, hybrid retrieval, reranking, prompt construction, structured prompt sources (sources provided to the model in the prompt), pipeline inspection, document inspection, and retrieval-mode comparison**, making it possible not only to ask questions over documents, but also to understand **why** a given answer was produced.

---

# 🚀 Live Demo

👉 **Hugging Face Space:**  
https://huggingface.co/spaces/amosbangmo/ragcraft

The demo allows you to:

- create an account
- manage multiple projects
- upload and reindex documents
- ask questions over project-specific knowledge bases
- inspect indexed document assets
- inspect the full RAG pipeline
- compare **FAISS-only retrieval** vs **Hybrid retrieval**

---

# ✨ Key Features

## Multi-user Platform

- User authentication with **SQLite**
- Secure password hashing with **bcrypt**
- User-scoped projects and isolated workspaces
- Profile management with avatar support

## Document Intelligence

- Document ingestion for **PDF, DOCX, PPTX**
- Parsing with **Unstructured**
- Text, table, and image extraction
- Title-aware semantic chunking
- Document reindexing from stored source files

## Retrieval Pipeline

- Semantic retrieval with **FAISS**
- Lexical retrieval with **BM25**
- Optional **Hybrid retrieval (FAISS + BM25)**
- Optional **query rewriting**
- Asset-level reranking with **CrossEncoder**
- Asset-level retrieval instead of fixed-size chunks

## Prompting & Grounding

- Prompt construction from **top reranked raw assets**
- Structured prompt sources (labeled sources in the prompt; not necessarily cited verbatim in the answer)
- Inline references to prompt source labels in final answers when the model cites evidence
- Prompt transparency through Retrieval Inspector

## Multimodal Asset Storage

- Structured storage of extracted document elements
- Asset types:
  - text
  - HTML tables
  - images (base64)
- Centralized **SQLite asset store**

## Inspection & Debugging

- Document inspection UI
- Retrieval inspector
- Toggleable **query rewrite**
- Toggleable **hybrid retrieval**
- **FAISS vs Hybrid comparison page**

---

# 🏗️ Architecture Overview

- **FastAPI** under **`api/src/interfaces/http/`** (ASGI entry **`api/main.py`**) is the **HTTP backend** — OpenAPI at `/docs`. This is the **integration contract** for SPAs, scripts, and automation.
- **Streamlit** (`frontend/app.py`, `frontend/src/pages/`, `frontend/src/components/`) is a **reference UI client**. It talks to capabilities only through **`BackendClient`** (`frontend/src/services/protocol.py`). Pages and components must **not** import `domain`, `application`, `composition`, or `interfaces` directly (enforced by architecture tests).
- **Default Streamlit mode** is **`RAGCRAFT_BACKEND_CLIENT=http`**: the UI calls the API over HTTP like any other client. **`in_process`** builds a **`BackendApplicationContainer`** inside the Streamlit process (no uvicorn) for fast local work — same use cases, different transport.
- **Angular or other SPAs** should use the **same HTTP API**: obtain a JWT from `POST /auth/login` or `/auth/register`, then send `Authorization: Bearer <access_token>` on scoped routes.

```text
User (Browser)
      │
      ├──────────────────────────────┐
      ▼                              ▼
Streamlit UI                  Angular / API clients
      │                              │
      │  BackendClient               │  HTTP (+ Bearer JWT)
      │  (in-process OR HTTP)        │
      ▼                              ▼
BackendApplicationContainer (use cases + infrastructure services)
      │
      ▼
Document Processing
(Unstructured extraction + chunking)
      │
      ▼
Retrieval Pipeline
(Query rewrite → FAISS / BM25 → merge → rerank)
      │
      ▼
Storage Layer
(SQLite rag_assets + project FAISS indexes)
      │
      ▼
Prompt Construction
      │
      ▼
LLM
```

**Architecture reference:** **`docs/README.md`** (index) · **`docs/architecture.md`** (layers) · **`docs/dependency_rules.md`** (imports + tests) · **`docs/migration_report_final.md`** (closure) · **`ARCHITECTURE_TARGET.md`** (short target summary) · **`api/tests/architecture/README.md`** (test matrix).

### Migration status (short)

| Done | Transitional / deprecated |
|------|---------------------------|
| FastAPI + use-case wiring, `BackendApplicationContainer`, HTTP E2E tests | Monolith trees under **`api/src/backend/`**, **`api/src/adapters/`** stay removed — implementations live under **`api/src/infrastructure/`** |
| Streamlit → `BackendClient`; architecture boundaries tested | Streamlit as **primary demo UI** until a SPA replaces it for product work |
| Domain without LangChain/FastAPI/Streamlit; `SummaryRecallDocument` for recall DTOs | **Bearer JWT** for HTTP API; rotate secrets and tune expiry for production |

### Where new logic should live

| Kind of change | Place |
|----------------|--------|
| Business rules, entities, ports | `api/src/domain/` |
| Orchestration, commands, HTTP wire DTOs | `api/src/application/use_cases/**` (and `api/src/application/http/wire/` for JSON shapes) |
| RAG, FAISS, SQLite, LLM, extraction | `api/src/infrastructure/` (`rag/`, `persistence/`, `evaluation/`, …) |
| SQLite port implementations | `api/src/infrastructure/persistence/sqlite/` |
| Wiring the graph | `api/src/composition/` |
| Streamlit/HTTP client seam | `frontend/src/services/` (`BackendClient`, Streamlit transcript); HTTP stubs → `api/src/application/frontend_support/` |

---

# 🔎 RAG Pipeline

```text
User query
      │
      ▼
Optional query rewriting
      │
      ▼
Recall retrieval
 ├── FAISS semantic search
 └── BM25 lexical search
      │
      ▼
Hybrid merge + deduplication
      │
      ▼
Raw asset rehydration from SQLite
      │
      ▼
Asset-level reranking
      │
      ▼
Top-N assets selected
      │
      ▼
Prompt construction
      │
      ▼
LLM answer (may reference prompt source labels inline)
```

Benefits:

- better recall on exact terms
- robustness on conversational queries
- higher answer precision
- reduced hallucinations
- full pipeline transparency

---

# 📦 Data Model

## Vector Layer

```text
FAISS index
└── embedding vectors for summary documents
```

## Asset Storage Layer

```text
SQLite database
├── users
└── rag_assets
    ├── text chunks
    ├── tables (HTML)
    └── images (base64)
```

Assets are rehydrated from SQLite during retrieval to build the final prompt.

---

# 📁 Project Structure

```text
ragcraft/
│
├── api/
│   ├── main.py                  # ASGI entry (uvicorn: api.main:app)
│   ├── src/                     # PYTHONPATH: domain, application, infrastructure, composition, interfaces
│   │   ├── application/       # use_cases, orchestration/, rag/, dto/, frontend_support/, …
│   │   ├── composition/
│   │   ├── domain/
│   │   ├── infrastructure/    # rag/, evaluation/, persistence/, auth/, …
│   │   └── interfaces/http/     # FastAPI app, routers/, schemas/, dependencies
│   └── tests/                   # pytest: architecture/, api/, appli/, infra/, e2e/, …
├── frontend/
│   ├── app.py                   # Streamlit entry (run from frontend/)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/          # BackendClient, HTTP / in-process clients, Streamlit factory
│   │   ├── state/
│   │   ├── viewmodels/
│   │   └── utils/
│   └── tests/                   # streamlit/, ui/, …
├── docs/                        # architecture.md, api.md, dependency_rules.md, …
├── scripts/                     # validate_architecture, run_tests, lint, validate
├── data/
├── requirements.txt
├── ARCHITECTURE_TARGET.md
└── README.md
```

---

# ⚙️ Installation

## Clone

```bash
git clone https://github.com/amosbangmo/ragcraft.git
cd ragcraft
```

## Install

```bash
pip install -r requirements.txt
```

## Testing and architecture validation

Run from the **repository root**. Layout and import-boundary tests live under **`api/tests/architecture/`** (see **`docs/testing_strategy.md`**).

| Goal | Bash (Linux / macOS / Git Bash) | PowerShell |
|------|----------------------------------|------------|
| **Architecture only** (fast, blocking) | `./scripts/validate_architecture.sh` | `.\scripts\validate_architecture.ps1` |
| **Lint + architecture** (CI-style quick check) | `./scripts/validate.sh` | `.\scripts\validate.ps1` |
| **Full pytest suite** (architecture first, then the rest) | `./scripts/run_tests.sh` | `.\scripts\run_tests.ps1` |
| **Lint only** | `./scripts/lint.sh` | `.\scripts\lint.ps1` |

Equivalent manual invocation for architecture tests:

```bash
export PYTHONPATH=api/src:frontend/src:api/tests   # Linux/macOS Git Bash
python -m pytest api/tests/architecture -q
```

Optional: from **`api/`**, `pytest` runs only **`tests/architecture`** (see **`api/pyproject.toml`**).

**Typing:** incremental **`mypy`** is documented in **`docs/testing_strategy.md`**; it is not part of the default lint script.

## Run

### Streamlit (default local UI)

```bash
cd frontend
streamlit run app.py
```

Use **`PYTHONPATH`** as in **`docs/README.md`** (repo root + **`api/src`** + **`frontend/src`**) so `api` and Streamlit imports resolve.

### FastAPI backend (HTTP API)

Use a second terminal if you want OpenAPI docs or to point Streamlit at the API:

```bash
export PYTHONPATH=$(pwd)   # Linux/macOS — repository root
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

PowerShell: `$env:PYTHONPATH = (Get-Location).Path` then the same `uvicorn` command.

- **Docs:** http://127.0.0.1:8000/docs  
- **Streamlit + API:** set `RAGCRAFT_BACKEND_CLIENT=http` and `RAGCRAFT_API_BASE_URL` (see **`docs/README.md`** — local development).

### Environment variables

Create `.env`:

```
OPENAI_API_KEY=your_api_key
```

---

# 🧪 Technology Stack

## Core

- Python
- FastAPI (HTTP API, `api/src/interfaces/http/`, entry `api/main.py`)
- Streamlit
- LangChain
- FAISS
- Unstructured
- SQLite

## Retrieval

- Sentence Transformers
- CrossEncoder
- BM25

## Utilities

- bcrypt
- pillow
- python-dotenv

---

# 🎯 What Makes This Project Different?

Many RAG demos only show:

- embeddings
- chunk retrieval
- LLM answering

RAGCraft demonstrates a **more realistic RAG system** including:

- multimodal ingestion
- asset-level retrieval
- hybrid search
- reranking
- pipeline inspection
- retrieval comparison tooling

This makes the system ideal for **portfolio demonstration and RAG system education**.

---

# 🛣️ Roadmap

## Evaluation

- RAG evaluation datasets
- answer correctness scoring
- prompt-source precision metrics
- regression testing

## LLM-as-a-Judge

- groundedness scoring
- prompt source alignment checks
- hallucination detection

## Retrieval

- weighted hybrid search
- metadata filtering
- query intent classification
- contextual compression

## Observability

- pipeline latency metrics
- retrieval analytics dashboard
- query logs

## Multimodal QA

- image understanding
- table-aware QA
- layout-aware prompting

## System Architecture

- FastAPI backend
- background ingestion workers
- API layer
- Postgres support

---

# ⚠️ Disclaimer

This project is developed for educational and portfolio purposes only and is not affiliated with any existing product named “RAGCraft”.

---

# 👤 Author

**Amos Bangmo**  
Software & AI Engineer
