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

RAGCraft is a **multi-user, multi-project RAG platform** designed to showcase how modern document intelligence systems can be built with inspectable retrieval pipelines, multimodal document extraction, and structured asset storage.

Key capabilities include:

- 🔎 Inspectable retrieval pipelines
- 📦 Structured multimodal document assets
- 🧠 Two-stage retrieval with reranking

---

# 🎥 Demo

🎥 **[GIF – Application Demo]**

*(Add a GIF showing: upload → ask question → inspect retrieval - to be done)*

```text
Upload document
      ↓
Ask question
      ↓
Inspect retrieved assets
      ↓
See generated answer
```

---

# 📷 Application Screenshots

### Chat Interface

📷 **[SCREENSHOT – Chat UI]**

*(Show the conversation with citations - to be done)*

---

### Document Inspector

📷 **[SCREENSHOT – Inspect Document Modal]**

*(Show text / tables / images extracted from a document - to be done)*

---

### Retrieval Inspector

📷 **[SCREENSHOT – Retrieval Inspection Page]**

*(Show retrieved summaries, assets selected, and final prompt - to be done)*

---

# 🚀 Key Features

### User Management
- 👤 **User authentication with SQLite**
- 🔑 **Secure password hashing (bcrypt)**
- 📁 **User-scoped projects**

### Document Intelligence
- 📄 **Document ingestion** (PDF, DOCX, PPTX)
- 🧩 **Advanced parsing** using **Unstructured**
- 🪄 **Table and image extraction**
- ✂️ **Semantic chunking using title-aware chunking**

### Retrieval & RAG
- 🔎 **Vector search with FAISS**
- 🧠 **Two-stage retrieval pipeline**
  - Large recall via embeddings
  - Strict reranking of candidate assets
- 📚 **Raw asset retrieval injected into prompts**

### Asset-level Retrieval
- 📦 Structured storage of extracted document elements
- 🧠 Asset-level retrieval instead of traditional fixed-size chunk retrieval
- 🔍 Transparent prompt reconstruction

### Multimodal Asset Storage
- 📦 Structured storage of:
  - text chunks
  - tables (HTML representation)
  - images (base64 payload)
- 🗄 **SQLite-based document store**

### Inspection & Debugging Tools
- 🔍 **Document inspection UI**
- 🔎 **Retrieval inspection page**
- 🧠 **Full RAG pipeline visibility**

---

# 🏗️ System Architecture

📊 **[ARCHITECTURE DIAGRAM]**

*(Draw a simple diagram and insert here - to be done)*

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
(FAISS + reranking)
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

RAGCraft stores data in **two complementary layers**.

## Vector layer

Used for fast semantic retrieval.

```text
FAISS index
└── embedding vectors
```

## Asset storage layer

Document assets are stored in a **central SQLite database**.

```text
SQLite database
├── users
└── rag_assets
    ├── text chunks
    ├── tables (HTML representation)
    └── images (base64 payload)
```

The `rag_assets` table stores extracted elements from documents and is used to reconstruct prompts during retrieval.


This architecture ensures:

- fast retrieval
- traceability of answers
- prompt transparency
- easier debugging of RAG pipelines

---

# 🧩 Data Isolation Model

RAGCraft uses a **hybrid storage model**:

1️⃣ **Application data stored in SQLite**  
2️⃣ **Project-level vector indexes stored on disk**

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

The SQLite database stores:

- user accounts
- extracted document assets

Vector indexes remain **project-specific** and are stored on disk using FAISS.


---

# 🔐 Authentication

User accounts are stored in the **main SQLite application database** in the `users` table.

Passwords are securely stored using **bcrypt hashing**.

Authentication features include:

- account creation
- login
- secure password hashing
- user-scoped project isolation

This lightweight model allows RAGCraft to demonstrate **multi-user RAG architecture** without requiring external infrastructure.

---

# 🔎 RAG Pipeline (Step-by-Step)

This system follows a **two-stage retrieval pipeline**.

```text
User query
      ↓
Embedding search (FAISS)
      ↓
Top-K candidate summaries
      ↓
Reranking
      ↓
Top-N assets selected
      ↓
Raw asset loading
      ↓
Prompt construction
      ↓
LLM answer
```

Benefits:

- higher recall retrieval
- improved precision
- fewer hallucinations
- grounded responses

---

# 🧠 Product & Technical Decisions

### Why SQLite-based user management?

RAGCraft stores user accounts in a lightweight **SQLite authentication store**.

This approach provides:

- persistent user accounts
- credential-based authentication
- isolated workspaces per user
- minimal infrastructure complexity

SQLite was chosen because it is:

- lightweight and embedded
- ideal for single-container deployments
- sufficient for portfolio-grade multi-user applications

### Why FAISS?

- Lightweight and fast
- Perfect for single-container environments
- Ideal for portfolio-grade RAG systems

### Why SQLite?

RAGCraft uses a lightweight **SQLite database** to store:

- user accounts
- extracted document assets

This approach keeps the system simple while still enabling:

- multi-user support
- persistent asset storage
- efficient prompt reconstruction

### Why Streamlit?

- Rapid iteration
- Clear workflows
- Ideal for AI demos

---

# 🧪 Current Scope & Limitations

RAGCraft is intentionally designed as a **portfolio-grade system**, not a production SaaS.

Current limitations include:

- SQLite-based authentication (not designed for high-scale production)
- Single-container deployment
- No distributed ingestion workers yet
- No external object storage

These trade-offs keep the system **simple to deploy, inspect, and experiment with**.

---

# 🎯 What Makes This RAG System Different?

Most RAG demos simply embed documents and retrieve text chunks.

RAGCraft goes further by introducing:

- asset-level document storage
- two-stage retrieval pipelines
- inspection tooling for debugging RAG
- multimodal document extraction

---

# 🛣️ Roadmap

### Retrieval Improvements
- Hybrid search (**BM25 + embeddings**)
- Retrieval score comparison tools
- Query analytics

### Evaluation Suite
- RAG evaluation datasets
- Answer correctness scoring
- Retrieval success metrics
- Regression testing for RAG pipelines

### LLM-as-a-Judge
- Groundedness scoring
- Citation verification
- Answer relevance evaluation

### Observability
- Retrieval analytics
- Pipeline metrics
- Prompt inspection improvements

### Multimodal Intelligence
- Image understanding
- Table-aware question answering

### System Architecture
- Optional **FastAPI backend**
- Background ingestion workers
- API access layer

### Agentic Retrieval Workflows
- Tool-based retrieval agents
- Query rewriting
- Self-reflection loops
- Multi-step retrieval

### Dataset & Benchmarking
- Public evaluation datasets
- Benchmark comparisons
- Retrieval quality benchmarks

---

# ⚠️ Disclaimer

This project is developed for **educational and portfolio purposes only** and is not affiliated with any existing product named **“RAGCraft”**.

---

# 👤 Author

Developed by **Amos Bangmo**  
*Software & AI Engineer*