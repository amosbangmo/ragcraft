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

**RAGCraft** is a **multi-project Retrieval-Augmented Generation (RAG) system** designed as a **portfolio project** to demonstrate end-to-end AI product development.

It enables users to ingest unstructured documents, build isolated knowledge bases, and query them through a conversational interface.

## 🚀 Features

* 🔐 Session-based user isolation
* 📁 Multiple projects per user
* 📄 Document ingestion (PDF, DOCX, PPTX)
* 🧩 Parsing & chunking with **Unstructured**
* 🔎 Vector search with **FAISS**
* 🧠 RAG pipelines using **LangChain**
* 💬 Conversational UI with **Streamlit**
* ☁️ Fully deployed on **Hugging Face Spaces**

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

## Data isolation model

```
data/
└── user_<session_id>/
    ├── project_1/
    │   └── faiss_index/
    └── project_2/
        └── faiss_index/

```

Each project has:

* its own documents
* its own vector index
* its own conversation history

## 🧠 Product & Technical Decisions

**Why session-based users?**

* Simplifies deployment on Hugging Face Spaces
* Avoids premature authentication complexity
* Still guarantees project isolation

**Why FAISS?**

* Lightweight and reliable
* Well-suited for single-container deployments
* Ideal for portfolio and MVP-grade systems

**Why Streamlit?**

* Rapid iteration
* Clear user workflows
* Excellent for AI demos and internal tools

## 🧪 Current Scope & Limitations

* No persistent authentication
* No concurrent multi-user guarantees
* Portfolio-grade security model

These trade-offs are intentional and documented.

## 🛣️ Roadmap

**Next versions may include**

* FastAPI backend
* JWT authentication
* Hybrid search (BM25 + embeddings)
* RAG evaluation dashboard
* LLM-as-a-Judge pipelines
* Advanced monitoring

## ⚠️ Disclaimer

This project is developed for **educational and portfolio purposes only** and is not affiliated with any existing product named “RAGCraft”.

## 👤 Author

Developed by *Amos Bangmo* (Software & AI Engineer)
>>>>>>> 6d1d13e (Fixing short_description config)
