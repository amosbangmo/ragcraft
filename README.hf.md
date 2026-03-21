---
title: RAGCraft
emoji: 🚀
colorFrom: red
colorTo: yellow
sdk: docker
python_version: 3.13.11
app_file: streamlit_app.py
app_port: 8501
tags:
  - rag
  - llm
  - document-ai
  - multimodal
  - vector-search
  - faiss
  - langchain
  - streamlit
  - unstructured
  - retrieval
  - semantic-search
pinned: true
short_description: Multi-project RAG system turning documents into answers
---

# 📚 RAGCraft

> **A portfolio-grade Retrieval-Augmented Generation (RAG) platform demonstrating how modern document intelligence systems can be built.**

RAGCraft is a **multi-user, multi-project RAG platform** designed to showcase how modern document intelligence systems can be built with **inspectable retrieval pipelines, hybrid retrieval, query rewriting, multimodal document extraction, and structured asset storage**.

Key capabilities include:

- 🔎 Inspectable retrieval pipelines
- 🔀 Hybrid retrieval (FAISS + BM25)
- ✍️ Query rewriting before retrieval
- 📦 Structured multimodal document assets
- ⚖️ Retrieval comparison tooling (FAISS vs Hybrid)

---

# 🎥 Demo

🎥 **[GIF – Application Demo]**

*(Add a GIF showing: upload → ask question → inspect retrieval → compare retrieval modes)*

```text
Upload document
      ↓
Ask question
      ↓
Inspect retrieved assets
      ↓
Analyze pipeline
      ↓
Compare FAISS vs Hybrid retrieval
```

---

# 📷 Application Screenshots

## Chat Interface

📷 **[SCREENSHOT – Chat UI]**

*(Conversation with prompt sources listed in the UI)*

---

## Document Inspector

📷 **[SCREENSHOT – Inspect Document Modal]**

*(Shows text / tables / images extracted from a document)*

---

## Retrieval Inspector

📷 **[SCREENSHOT – Retrieval Inspection Page]**

*(Shows retrieval stages and final prompt)*

---

# 🚀 Key Features

## User Management

- 👤 **User authentication with SQLite**
- 🔑 **Secure password hashing (bcrypt)**
- 📁 **User-scoped projects**
- 🧑‍💻 Profile management and avatars

## Document Intelligence

- 📄 **Document ingestion** (PDF, DOCX, PPTX)
- 🧩 **Advanced parsing using Unstructured**
- 🪄 **Table and image extraction**
- ✂️ **Title-aware semantic chunking**
- 🔄 Document reindexing

## Retrieval & RAG

- 🔎 **Semantic search with FAISS**
- 📚 **Lexical search with BM25**
- 🔀 **Hybrid retrieval pipeline**
- ✍️ **Query rewriting for better retrieval**
- 🧠 **CrossEncoder reranking**
- 📦 **Asset-level retrieval injected into prompts**

## Asset-level Retrieval

- 📦 Structured storage of extracted document elements
- 🧠 Retrieval based on document assets instead of fixed chunks
- 🔍 Transparent prompt reconstruction

## Multimodal Asset Storage

Assets stored in SQLite:

- text chunks
- HTML tables
- images (base64)

## Inspection & Debugging Tools

- 🔍 **Document inspection UI**
- 🔎 **Retrieval inspection page**
- ⚙️ Toggle **query rewrite**
- ⚙️ Toggle **hybrid retrieval**
- ⚖️ **FAISS vs Hybrid comparison page**

---

# 🏗️ System Architecture

```text
User (Browser)
      ↓
Streamlit UI
      ↓
Application Services
      ↓
Document Processing
(Unstructured extraction + chunking)
      ↓
Retrieval Pipeline
(Query rewrite → FAISS / BM25 → merge → rerank)
      ↓
Application Database
(SQLite: users + rag_assets)
      ↓
Prompt Construction
      ↓
LLM
```

---

# 📦 Data Model

RAGCraft uses **two complementary storage layers**.

## Vector layer

Used for semantic retrieval.

```text
FAISS index
└── embedding vectors
```

## Asset storage layer

```text
SQLite database
├── users
└── rag_assets
    ├── text chunks
    ├── tables
    └── images
```

Assets are rehydrated from SQLite during retrieval to build grounded prompts.

---

# 🧩 Data Isolation Model

```text
data/
├── ragcraft.db
│   ├── users
│   └── rag_assets
│
└── users/
    └── <user_id>/
        └── projects/
            ├── project_1/
            │   ├── documents/
            │   └── faiss_index
            │
            └── project_2/
                ├── documents/
                └── faiss_index
```

SQLite stores:

- users
- extracted assets

FAISS indexes remain **project-specific**.

---

# 🔐 Authentication

User accounts are stored in the **SQLite application database**.

Passwords are securely stored using **bcrypt hashing**.

Features include:

- account creation
- login
- password change
- profile management
- user-scoped project isolation

---

# 🔎 RAG Pipeline

```text
User query
      ↓
Query rewriting
      ↓
Recall retrieval
  ├─ FAISS semantic search
  └─ BM25 lexical search
      ↓
Hybrid merge
      ↓
Raw asset loading
      ↓
CrossEncoder reranking
      ↓
Top-N assets selected
      ↓
Prompt construction
      ↓
LLM answer
```

Benefits:

- improved recall
- better robustness on vague queries
- reduced hallucinations
- transparent answer grounding

---

# 🧠 Product & Technical Decisions

## Why Hybrid Retrieval?

Combining **semantic search and lexical search** improves recall for:

- exact terminology
- acronyms
- structured content like tables

## Why Asset-Level Retrieval?

Instead of retrieving arbitrary chunks, RAGCraft retrieves **document assets** such as:

- text sections
- tables
- figures

This improves interpretability and debugging.

## Why SQLite?

SQLite provides:

- embedded persistence
- zero infrastructure
- multi-user capability

Ideal for **portfolio-scale RAG systems**.

## Why Streamlit?

- rapid prototyping
- interactive AI demos
- easy pipeline inspection

---

# 🧪 Current Scope & Limitations

RAGCraft is intentionally designed as a **portfolio-grade system**, not a production SaaS.

Current limitations:

- SQLite database
- single-container deployment
- no distributed ingestion workers
- limited dataset evaluation tools

These trade-offs keep the system **simple to deploy and explore**.

---

# 🎯 What Makes This RAG System Different?

Most RAG demos only show:

- embeddings
- chunk retrieval
- LLM answers

RAGCraft adds:

- multimodal document extraction
- hybrid retrieval
- query rewriting
- reranking
- pipeline inspection
- retrieval comparison tooling

This makes the system **transparent, debuggable, and educational**.

---

# 🛣️ Roadmap

## Evaluation & Benchmarking

- gold QA datasets per project
- answer correctness scoring
- prompt-source vs expected overlap metrics (reported under ``prompt_*`` benchmark fields)
- automated RAG regression tests
- downloadable benchmark reports

## LLM-as-a-Judge

- groundedness scoring
- prompt source alignment checks (judge; uses prompt sources and retrieved context)
- hallucination detection
- answer relevance scoring

## Retrieval Improvements

- metadata-aware retrieval filters
- query intent classification
- contextual compression
- section-aware retrieval

## Observability

- query logs
- per-stage latency metrics
- ingestion diagnostics
- retrieval analytics dashboard

## Multimodal Intelligence

- richer image understanding
- table-aware QA
- layout-aware prompting

## System Architecture

- optional FastAPI backend
- async ingestion workers
- API access layer
- experiment tracking

## Product Features

- downloadable retrieval comparison reports
- saved evaluation suites
- configurable retrieval settings in UI
- project analytics dashboard

---

# ⚠️ Disclaimer

This project is developed for **educational and portfolio purposes only** and is not affiliated with any existing product named **“RAGCraft”**.

---

# 👤 Author

Developed by **Amos Bangmo**  
*Software & AI Engineer*
