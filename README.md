
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

- **FastAPI (`apps/api/`)** is the **HTTP backend** — OpenAPI at `/docs`. This is the **integration contract** for SPAs, scripts, and automation.
- **Streamlit** (`streamlit_app.py`, `pages/`, `src/ui/`) is a **reference UI client**. It talks to capabilities only through **`BackendClient`** (`src/frontend_gateway/protocol.py`). It must **not** import `src.domain`, `src.infrastructure`, `src.composition`, or `apps.api` directly (enforced by architecture tests).
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

**Architecture reference:** `ARCHITECTURE_TARGET.md` (short) · **`docs/README.md`** (index) · **`docs/migration_report_final.md`** (closure report) · `tests/architecture/README.md` (import guardrails).

### Migration status (short)

| Done | Transitional / deprecated |
|------|---------------------------|
| FastAPI + use-case wiring, `BackendApplicationContainer`, HTTP E2E tests | Legacy **`src/backend/`**, **`src/adapters/`** removed — use **`infrastructure.adapters`** |
| Streamlit → `BackendClient`; architecture boundaries tested | Streamlit as **primary demo UI** until a SPA replaces it for product work |
| Domain without LangChain/FastAPI/Streamlit; `SummaryRecallDocument` for recall DTOs | **Bearer JWT** for HTTP API; rotate secrets and tune expiry for production |

### Where new logic should live

| Kind of change | Place |
|----------------|--------|
| Business rules, entities, ports | `src/domain/` |
| Orchestration, commands, HTTP wire DTOs | `src/application/use_cases/**` (and `application/http/wire.py` for JSON shapes) |
| RAG, FAISS, SQLite, LLM, extraction | `src/infrastructure/` (`adapters/`, `persistence/`, `vectorstores/`, …) |
| SQLite port implementations | `src/infrastructure/adapters/sqlite/` |
| Wiring the graph | `src/composition/` |
| Streamlit/HTTP client seam | `src/frontend_gateway/` (`BackendClient`, Streamlit chat transcript); HTTP placeholders → `src/application/frontend_support/` |

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
├── apps/api/                    # FastAPI — HTTP backend, OpenAPI, Depends → container
├── streamlit_app.py             # Streamlit entry
├── pages/                       # Streamlit multipage app
├── src/
│   ├── application/             # Use cases, policies, HTTP wire helpers, frontend_support stubs
│   ├── auth/
│   ├── composition/             # build_backend(), BackendApplicationContainer
│   ├── core/                    # config, paths, shared errors (Streamlit session helpers here)
│   ├── domain/                  # Entities, ports, SummaryRecallDocument, no framework imports
│   ├── frontend_gateway/        # BackendClient, HttpBackendClient, InProcessBackendClient
│   ├── infrastructure/          # adapters/, persistence/, vectorstores/, …
│   │   └── adapters/sqlite/     # SQLite port implementations (users, assets, settings)
│   └── ui/                      # Streamlit widgets (no direct domain/infra imports)
├── docs/                        # Architecture, RAG flow, dependency rules, testing, final migration report
├── tests/
│   ├── architecture/            # Layer boundary + orchestration guardrails
│   ├── apps_api/                # FastAPI contract tests
│   └── infrastructure_services/ # Unit tests for infrastructure.adapters
├── data/
├── requirements.txt
├── ARCHITECTURE_TARGET.md       # Short runtime layout (read this first)
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
streamlit run streamlit_app.py
```

Set `PYTHONPATH` to the repo root if imports fail (see `apps/api/main.py` for the same pattern).

### FastAPI backend (HTTP API)

Use a second terminal if you want OpenAPI docs or to point Streamlit at the API:

```bash
export PYTHONPATH=$(pwd)   # Linux/macOS
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
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
- FastAPI (HTTP API, `apps/api/`)
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
