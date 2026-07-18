"""
config.py — Single Source of Truth for all RAG hyperparameters.

Every tunable parameter is read from environment variables so that
experiments can be run by simply changing .env values and restarting
the server — no code edits needed.

Experiment workflow:
    # Dense baseline
    RETRIEVAL_MODE=dense TOP_K=6 uvicorn main:app --port 8000

    # Hybrid BM25+RRF
    RETRIEVAL_MODE=hybrid TOP_K=6 uvicorn main:app --port 8000

    # Hybrid + CrossEncoder reranker
    RETRIEVAL_MODE=hybrid_rerank TOP_K=6 RERANK_TOP_N=50 uvicorn main:app --port 8000

    # Enable evaluation CSV logging
    EVALUATION_MODE=true uvicorn main:app --port 8000
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file ────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


# ── Helper functions for robust parsing ───────────────────────────────────────
def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if not val:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default

def _get_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if not val:
        return default
    try:
        return float(val.strip())
    except ValueError:
        return default


class Config:
    # ── App Configuration ─────────────────────────────────────────────────────
    APP_NAME    = os.getenv("NEXT_PUBLIC_APP_NAME", "Academic Research Assistant")
    BACKEND_URL = os.getenv("NEXT_PUBLIC_BACKEND_URL", "http://127.0.0.1:8001")

    # ── LLM & Embedding API Keys ──────────────────────────────────────────────
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

    # ── Qdrant Configuration ──────────────────────────────────────────────────
    QDRANT_API_KEY     = os.getenv("QDRANT_API_KEY", "")
    QDRANT_CLUSTER_URL = os.getenv("QDRANT_CLUSTER_URL", "")

    # ── LLM Model ─────────────────────────────────────────────────────────────
    LLM_MODEL      = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    LLM_TEMPERATURE = _get_float("LLM_TEMPERATURE", 0.3)

    # ── Qdrant Collection ─────────────────────────────────────────────────────
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "academic_rag_demo")

    # ── Chunking Parameters ───────────────────────────────────────────────────
    CHUNK_SIZE    = _get_int("CHUNK_SIZE", 500)
    CHUNK_OVERLAP = _get_int("CHUNK_OVERLAP", 50)

    # ── Retrieval Parameters ──────────────────────────────────────────────────
    TOP_K = _get_int("TOP_K", 6)
    RERANK_TOP_N = _get_int("RERANK_TOP_N", 50)

    # ── Retrieval Mode ────────────────────────────────────────────────────────
    RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense")  # dense | hybrid | hybrid_rerank

    # ── Evaluation Mode ───────────────────────────────────────────────────────
    EVALUATION_MODE = os.getenv("EVALUATION_MODE", "false").lower() == "true"

    # ── Embedding Model Config ────────────────────────────────────────────────
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3")
    VECTOR_SIZE     = _get_int("VECTOR_SIZE", 1024)

    # ── BM25 Config ───────────────────────────────────────────────────────────
    BM25_CORPUS_LIMIT = _get_int("BM25_CORPUS_LIMIT", 2000)

    # ── Ingestion Batch Config ─────────────────────────────────────────────────
    INGEST_BATCH_SIZE    = _get_int("INGEST_BATCH_SIZE", 15)
    INGEST_BATCH_SLEEP_S = _get_float("INGEST_BATCH_SLEEP_S", 21.0)

    @classmethod
    def validate(cls):
        """Validates that all critical API credentials are present. Exits on failure."""
        missing = []
        if not cls.VOYAGE_API_KEY:
            missing.append("VOYAGE_API_KEY")
        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")
        if not cls.QDRANT_API_KEY:
            missing.append("QDRANT_API_KEY")
        if not cls.QDRANT_CLUSTER_URL:
            missing.append("QDRANT_CLUSTER_URL")

        # Validate retrieval mode is one of the supported values
        valid_modes = {"dense", "hybrid", "hybrid_rerank"}
        if cls.RETRIEVAL_MODE not in valid_modes:
            print(f"❌ Invalid RETRIEVAL_MODE '{cls.RETRIEVAL_MODE}'. Must be one of: {valid_modes}")
            # Do not exit, just default to dense
            cls.RETRIEVAL_MODE = "dense"

        if missing:
            print(f"❌ Missing critical credentials: {', '.join(missing)}")
            # On Vercel, exiting here crashes the whole serverless function with 500.
            # We just print the error and let the specific API routes fail gracefully.

        print(f"✅ Config loaded | mode={cls.RETRIEVAL_MODE} | top_k={cls.TOP_K} | "
              f"chunk_size={cls.CHUNK_SIZE} | overlap={cls.CHUNK_OVERLAP} | "
              f"eval={cls.EVALUATION_MODE}")

# Validate as soon as config is imported so failures surface early.
Config.validate()
