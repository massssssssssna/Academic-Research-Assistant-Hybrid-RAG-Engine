# Academic & Research Assistant: Hybrid RAG Engine

The **Academic & Research Assistant** is a high-performance, strictly constrained Retrieval-Augmented Generation (RAG) system built exclusively for educational, academic, and research-oriented tasks. Designed to eliminate AI hallucinations, this application ensures that all answers are rigorously grounded in user-provided literature, such as research PDFs and CSV datasets.

At the core of the system is a custom **Hybrid Search Architecture** that maximizes retrieval accuracy by ensembling two distinct search methodologies:
1. **Semantic Search:** Powered by **Qdrant** (Vector Database) and **VoyageAI** embeddings, enabling the system to understand the deep contextual meaning and semantic intent of complex academic queries.
2. **Lexical Search:** Powered by **BM25**, guaranteeing that specific scientific terminologies, author names, and exact phrasing within papers are never overlooked.

Once the most relevant document chunks are retrieved and deduplicated, the context is synthesized by **LLaMA-3 (8B)** via the ultra-fast **Groq API**, ensuring lightning-fast inference alongside high-quality reasoning.

## Key Features

* **Strict Domain Guardrails:** The assistant utilizes robust anti-hallucination system prompts. It is designed to explicitly refuse non-academic, unethical, or irrelevant queries, ensuring the chatbot remains a dedicated research tool.
* **Precise Source Citations:** Every generated response is backed by granular metadata. The system provides the exact source file name, page numbers, and text snippets used to formulate the answer, allowing researchers to instantly verify claims.
* **Automated Data Ingestion:** Features a streamlined API pipeline that automatically extracts `.zip` archives, scans directories for documents, and optimally chunks texts using LangChain's Recursive Character splitting.
* **Modern Tech Stack:** Built with an asynchronous **FastAPI** (Python) backend and a highly responsive **Next.js** (React) frontend.

## Getting Started

### Prerequisites

Ensure you have the following installed:
- [Node.js](https://nodejs.org/) (v18+)
- [Python 3.9+](https://www.python.org/)

You will also need to configure your environment variables in a `.env` file. (Refer to `.env.example`).

### 1. Setup the Backend (FastAPI)

```bash
# Create and activate a virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Mac/Linux: source .venv/bin/activate

# Install dependencies (assuming you have a requirements.txt)
pip install -r requirements.txt

# Run the backend server
python main.py
```
*The backend will run on `http://127.0.0.1:8000`.*

### 2. Setup the Frontend (Next.js)

```bash
# Install NPM packages
npm install

# Run the development server
npm run dev
# OR: npx next dev --turbopack
```
*The frontend will run on `http://localhost:3000`.*

## Evaluation Pipeline
The system includes a dedicated evaluation pipeline to benchmark different retrieval strategies (Dense, Hybrid, and Hybrid + Reranking) using a predefined `golden_dataset.json`. The pipeline automatically logs queries, computes metrics (Precision, Recall, MRR, nDCG), and generates a comprehensive `evaluation_report.md`.

### Usage

1. Place your research PDFs and CSVs in the `data/extracted_data` folder (or upload them).
2. Trigger the ingestion pipeline (via the UI or the `/api/upload` endpoint).
3. Start chatting with your research material!

---

*Built with Next.js, FastAPI, LangChain, Qdrant, VoyageAI, and Groq.*
