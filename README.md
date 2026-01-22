<<<<<<< HEAD
# ragcraft
RAGCraft is a **multi-user, multi-project RAG platform** designed to showcase how modern document intelligence systems can be built with inspectable retrieval pipelines, multimodal document extraction, and structured asset storage.
=======
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
  - streamlit
  - Unstructured
  - LangChain
  - FAISS
  - OpenAI
pinned: true
short_description: Multi-project RAG system turning documents into answers
---

# 📚 RAGCraft

> **Multi-project Retrieval-Augmented Generation system turning documents into answers**

**RAGCraft** is a **portfolio-grade Retrieval-Augmented Generation (RAG) system** designed to demonstrate how to build **reliable, end-to-end RAG applications** beyond simple demos.

It allows users to create multiple projects, ingest unstructured documents, and interact with isolated knowledge bases through a conversational interface.

---

## 🚀 Key Features

- 🔐 **Session-based user isolation**
- 📁 **Multiple projects per user**
- 📄 **Document ingestion** (PDF, DOCX, PPTX)
- 🧩 **Parsing & chunking** with **Unstructured**
- 🔎 **Vector search** using **FAISS**
- 🧠 **RAG pipelines** orchestrated with **LangChain**
- 💬 **Conversational UI** built with **Streamlit**
- ☁️ **Fully deployed on Hugging Face Spaces**

---

## 🏗️ Architecture Overview

```
User (Browser)
   ↓
Streamlit UI (Multi-Page)
   ↓
RAG Orchestration (LangChain)
   ↓
FAISS Vector Store (per project)
   ↓
LLM
```

---

## Data Isolation Model

```
data/
└── user_<session_id>/
    ├── project_1/
    │   └── faiss_index/
    └── project_2/
        └── faiss_index/

```


Each project is fully isolated and contains:
- its own documents
- its own vector index
- its own conversation history

This design prevents knowledge leakage across projects and mirrors real-world multi-tenant RAG constraints.

---

## 🧠 Product & Technical Decisions

### Why session-based users?
- Simplifies deployment on Hugging Face Spaces
- Avoids premature authentication complexity
- Still guarantees per-user and per-project isolation

### Why FAISS?
- Lightweight and fast
- Well-suited for single-container environments
- Ideal for portfolio and MVP-grade RAG systems

### Why Streamlit?
- Rapid prototyping and iteration
- Clear, user-friendly workflows
- Widely adopted for AI demos and internal tools

---

## 🧪 Current Scope & Limitations

- No persistent authentication
- No concurrent multi-user guarantees
- Portfolio-grade security model

These trade-offs are **intentional**, documented, and aligned with the project’s educational goals.

---

## 🛣️ Roadmap

Planned future improvements include:
- FastAPI backend separation
- JWT-based authentication
- Hybrid search (BM25 + embeddings)
- RAG evaluation & monitoring dashboard
- LLM-as-a-Judge pipelines
- Advanced observability and analytics

---

## ⚠️ Disclaimer

This project is developed for **educational and portfolio purposes only** and is not affiliated with any existing product named **“RAGCraft”**.

---

## 👤 Author

<<<<<<< HEAD
Developed by *Amos Bangmo* (Software & AI Engineer)
>>>>>>> 6d1d13e (Fixing short_description config)
=======
Developed by **Amos Bangmo**  
*Software & AI Engineer*
>>>>>>> 739a7c5 (README enhancement)
