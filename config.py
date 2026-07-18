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
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # ── Qdrant Collection ─────────────────────────────────────────────────────
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "academic_rag_demo")

    # ── Chunking Parameters ───────────────────────────────────────────────────
    # Change CHUNK_SIZE to experiment with different granularities:
    #   300  → very fine-grained, high recall, low precision
    #   500  → balanced (default)
    #   700  → moderate context per chunk
    #   1000 → large chunks, high precision if relevant, low recall
    CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

    # ── Retrieval Parameters ──────────────────────────────────────────────────
    # TOP_K: how many chunks to pass to the LLM as context.
    #   Lower TOP_K → faster, less context noise
    #   Higher TOP_K → more coverage, more tokens consumed
    TOP_K = int(os.getenv("TOP_K", "6"))

    # RERANK_TOP_N: initial retrieval pool size for hybrid_rerank mode.
    # The reranker scores all RERANK_TOP_N candidates and returns TOP_K best.
    # Must be >= TOP_K. Typical: 20–50.
    RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "50"))

    # ── Retrieval Mode ────────────────────────────────────────────────────────
    # Controls which retrieval strategy is used at query time.
    #
    #   "dense"          → Voyage AI embeddings + Qdrant ANN only
    #   "hybrid"         → Dense + BM25 fused with Reciprocal Rank Fusion (RRF)
    #   "hybrid_rerank"  → Hybrid (pool=RERANK_TOP_N) → CrossEncoder reranker → TOP_K
    #
    # Change this single variable to switch experiments.
    RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense")  # dense | hybrid | hybrid_rerank

    # ── Evaluation Mode ───────────────────────────────────────────────────────
    # When True, every /api/chat call is logged to evaluation/{mode}_log.csv.
    # Set to "true" in .env before running benchmark queries.
    EVALUATION_MODE = os.getenv("EVALUATION_MODE", "false").lower() == "true"

    # ── Embedding Model Config ────────────────────────────────────────────────
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3")
    VECTOR_SIZE     = int(os.getenv("VECTOR_SIZE", "1024"))

    # ── BM25 Config ───────────────────────────────────────────────────────────
    # Maximum chunks to scroll from Qdrant for BM25 index construction.
    # Increase for very large collections; keep low for speed.
    BM25_CORPUS_LIMIT = int(os.getenv("BM25_CORPUS_LIMIT", "2000"))

    # ── Ingestion Batch Config ─────────────────────────────────────────────────
    # Voyage AI free tier: 3 RPM, 10k TPM.
    # Batch of 15 chunks with 21s sleep respects these limits.
    INGEST_BATCH_SIZE    = int(os.getenv("INGEST_BATCH_SIZE", "15"))
    INGEST_BATCH_SLEEP_S = float(os.getenv("INGEST_BATCH_SLEEP_S", "21"))

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
