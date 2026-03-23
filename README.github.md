
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
- Structured source citations
- Inline citation labels in final answers
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

```text
User (Browser)
      │
      ▼
Streamlit UI
      │
      ▼
Application Facade (RAGCraftApp)
      │
      ▼
Service Layer
(auth / ingestion / retrieval / reranking / prompt building)
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
├── api/src/          # domain, application, infrastructure, composition, interfaces/http
├── frontend/
│   ├── app.py        # Streamlit entry (Docker / local: run from frontend/)
│   └── src/          # pages, components, services (BackendClient)
├── api/tests/
├── frontend/tests/
├── data/
├── requirements.txt
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

## Run

```bash
cd frontend
streamlit run app.py
```

### Environment variables

Create `.env`:

```
OPENAI_API_KEY=your_api_key
```

---

# 🧪 Technology Stack

## Core

- Python
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
