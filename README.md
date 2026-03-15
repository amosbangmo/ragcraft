![Python](https://img.shields.io/badge/python-3.13-blue)
![Streamlit](https://img.shields.io/badge/streamlit-app-red)
![License](https://img.shields.io/badge/license-MIT-green)

# 📚 RAGCraft

> A portfolio-grade **Retrieval-Augmented Generation (RAG) system** demonstrating how modern document intelligence systems can be built with multimodal ingestion, inspectable retrieval pipelines, and asset-level document storage.

RAGCraft is a **multi-user, multi-project RAG platform** designed to showcase how reliable document intelligence systems can be implemented beyond simple chatbot demos.

The system supports **document ingestion, multimodal asset extraction, vector retrieval, reranking, and full pipeline inspection**, allowing users to understand how answers are generated from source documents.

---

# 🚀 Live Demo

You can try the application here:

👉 **Hugging Face Space:**  
https://huggingface.co/spaces/amosbangmo/ragcraft

The demo allows you to:

- create your account
- upload documents
- ask questions
- inspect retrieved assets
- analyze the RAG pipeline

---

# ✨ Key Features

### Multi-user Platform
- User authentication with **SQLite**
- Secure password hashing with **bcrypt**
- User-scoped projects

### Document Intelligence
- Document ingestion (**PDF, DOCX, PPTX**)
- Parsing with **Unstructured**
- Table and image extraction
- Title-aware semantic chunking

### Retrieval Pipeline
- Vector search using **FAISS**
- **Two-stage retrieval strategy**
  - high-recall embedding search
  - reranking of candidate assets
- Asset-level retrieval instead of fixed-size chunks

### Multimodal Asset Storage
- Structured storage of extracted document elements
- Asset types:
  - text
  - HTML tables
  - images (base64)
- Stored in a **central SQLite database**

### Inspection & Debugging Tools
- Document inspection UI
- Retrieval inspection page
- Full RAG pipeline visibility

---

# 🏗️ Architecture Overview

```text
User (Browser)
      │
      ▼
Streamlit UI
      │
      ▼
Application Services
      │
      ▼
Document Processing
(Unstructured extraction + chunking)
      │
      ▼
Retrieval Pipeline
(FAISS + reranking)
      │
      ▼
Application Database
(SQLite: users + rag_assets)
      │
      ▼
Prompt Construction
      │
      ▼
LLM
```

The system separates responsibilities between:

- document ingestion
- asset storage
- retrieval
- prompt generation
- answer generation

This architecture mirrors how production RAG systems are typically structured.

---

# 🔎 RAG Pipeline

This system follows a **two-stage retrieval pipeline**.

```text
User query
      │
      ▼
Embedding search (FAISS)
      │
      ▼
Top-K candidate summaries
      │
      ▼
Reranking
      │
      ▼
Top-N assets selected
      │
      ▼
Raw asset loading
      │
      ▼
Prompt construction
      │
      ▼
LLM answer
```

Benefits:

- improved recall
- higher answer precision
- reduced hallucinations
- transparent answer grounding

---

# 📦 Data Model

RAGCraft uses **two complementary storage layers**.

## Vector Layer

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

---

# 🧩 Data Isolation Model

RAGCraft uses a **hybrid storage model**:

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

Vector indexes remain **project-specific** and are stored on disk.


---

# 📁 Project Structure

```text
ragcraft/
│
├── streamlit_app.py        # Entry point
├── pages/                  # Streamlit pages
│
├── src/
│   ├── domain/             # Core models
│   ├── services/           # RAG pipeline logic
│   ├── infrastructure/     # storage, extraction
│   └── ui/                 # UI components
│
├── data/                   # Runtime data
│
├── requirements.txt
└── README.md
```


---

# ⚙️ Installation

## 1️⃣ Clone the repository

```bash
git clone https://github.com/amosbangmo/ragcraft.git
cd ragcraft
```

## 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the application

```bash
streamlit run streamlit_app.py
```

### Environment variables

Create a `.env` file:

OPENAI_API_KEY=your_api_key


---

# Authentication

Users are stored in a lightweight **SQLite database** and passwords are hashed using **bcrypt**.

Each user has isolated workspaces and projects.

---

# 🧪 Technology Stack

### Core stack

- Python
- Streamlit
- LangChain
- FAISS
- Unstructured

### Supporting libraries

- Sentence Transformers
- SQLite
- bcrypt

---

# Design Decisions

**FAISS**

Chosen for lightweight, fast semantic search suitable for single-node RAG systems.

**SQLite**

Used as an embedded application database storing users and extracted document assets.

**Streamlit**

Provides a simple interface for exploring the RAG pipeline and debugging retrieval results.

---

# 🎯 What Makes This RAG System Different?

Most RAG demos simply embed documents and retrieve text chunks.

RAGCraft goes further by introducing:

- asset-level document storage
- multimodal document extraction
- two-stage retrieval pipelines
- retrieval inspection tooling
- prompt transparency

These features make it easier to debug and understand how RAG systems generate answers.

---

# 🛣️ Roadmap

Planned improvements include:

### Retrieval
- Hybrid search (BM25 + embeddings)
- Retrieval score comparison tools
- Query analytics

### Evaluation
- RAG evaluation datasets
- Answer correctness scoring
- Retrieval success metrics
- RAG regression testing

### LLM-as-a-Judge
- groundedness scoring
- citation verification
- answer relevance evaluation

### Observability
- retrieval analytics
- pipeline metrics
- prompt inspection improvements

### Multimodal QA
- image understanding
- table-aware question answering

### System Architecture
- FastAPI backend
- background ingestion workers
- API access layer

---

# ⚠️ Disclaimer

This project is developed for educational and portfolio purposes only and is not affiliated with any existing product named “RAGCraft”.

---

# 👤 Author

**Amos Bangmo**  
*Software & AI Engineer*
