"""
evaluation.py — Per-Query Evaluation Logger.

When Config.EVALUATION_MODE is True, every call to the /api/chat endpoint
is automatically logged to a CSV file in the evaluation/ directory.

Each row captures:
    - The query and retrieved chunk IDs
    - Source PDFs retrieved
    - Retrieval latency, generation latency, and total latency
    - The active configuration (top_k, chunk_size, overlap, mode)

This creates the raw data needed for metrics.py to compute
Precision@K, Recall@K, MRR, nDCG, and Hit Rate.

Output files:
    evaluation/dense_log.csv          (when RETRIEVAL_MODE=dense)
    evaluation/hybrid_log.csv         (when RETRIEVAL_MODE=hybrid)
    evaluation/hybrid_rerank_log.csv  (when RETRIEVAL_MODE=hybrid_rerank)
"""

import os
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import Config

logger = logging.getLogger(__name__)

# ── Output directory ───────────────────────────────────────────────────────────
EVAL_DIR = os.path.join(os.path.dirname(__file__), "evaluation")

# ── CSV column headers ─────────────────────────────────────────────────────────
FIELDNAMES = [
    "timestamp",
    "query",
    "retrieval_mode",
    "top_k",
    "chunk_size",
    "chunk_overlap",
    "retrieved_chunk_ids",    # pipe-separated list of chunk_id integers
    "retrieved_point_ids",    # pipe-separated list of Qdrant point UUIDs
    "retrieved_sources",      # pipe-separated list of source filenames
    "retrieval_latency_ms",
    "generation_latency_ms",
    "total_latency_ms",
]


def _get_log_path(mode: str) -> str:
    """
    Returns the CSV file path for the given retrieval mode.
    Creates the evaluation/ directory if it doesn't exist.

    Args:
        mode: Retrieval mode string (dense, hybrid, hybrid_rerank).

    Returns:
        Absolute path to the CSV log file.
    """
    os.makedirs(EVAL_DIR, exist_ok=True)
    safe_mode = mode.replace(" ", "_").replace("/", "_")
    return os.path.join(EVAL_DIR, f"{safe_mode}_log.csv")


def log_query(
    query: str,
    results: List[Dict[str, Any]],
    retrieval_latency_ms: float,
    generation_latency_ms: float,
    mode: Optional[str] = None,
    top_k: Optional[int] = None,
) -> None:
    """
    Appends one evaluation row to the mode-specific CSV log file.

    This function is a no-op when Config.EVALUATION_MODE is False,
    so it can be called unconditionally in main.py without any if-guards.

    Args:
        query:                  The raw user query string.
        results:                List of result dicts returned by retrieval.retrieve().
                                Each must have: id, chunk_id, source.
        retrieval_latency_ms:   Time taken by the retrieval step in milliseconds.
        generation_latency_ms:  Time taken by the LLM generation step in milliseconds.
        mode:                   Retrieval mode used. Defaults to Config.RETRIEVAL_MODE.
        top_k:                  Top-K value used. Defaults to Config.TOP_K.

    Returns:
        None. Writes to disk as a side-effect.
    """
    # Early exit when evaluation mode is disabled
    if not Config.EVALUATION_MODE:
        return

    effective_mode = mode  if mode  is not None else Config.RETRIEVAL_MODE
    effective_top_k = top_k if top_k is not None else Config.TOP_K

    log_path = _get_log_path(effective_mode)

    # Determine if we need to write the header (first time file is created)
    write_header = not os.path.exists(log_path)

    # Flatten retrieved metadata into pipe-separated strings for CSV
    chunk_ids  = "|".join(str(r.get("chunk_id", "")) for r in results)
    point_ids  = "|".join(str(r.get("id", ""))       for r in results)
    sources    = "|".join(set(r.get("source", "")    for r in results))

    total_latency_ms = round(retrieval_latency_ms + generation_latency_ms, 2)

    row = {
        "timestamp":              datetime.utcnow().isoformat(),
        "query":                  query,
        "retrieval_mode":         effective_mode,
        "top_k":                  effective_top_k,
        "chunk_size":             Config.CHUNK_SIZE,
        "chunk_overlap":          Config.CHUNK_OVERLAP,
        "retrieved_chunk_ids":    chunk_ids,
        "retrieved_point_ids":    point_ids,
        "retrieved_sources":      sources,
        "retrieval_latency_ms":   round(retrieval_latency_ms,  2),
        "generation_latency_ms":  round(generation_latency_ms, 2),
        "total_latency_ms":       total_latency_ms,
    }

    try:
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_header:
                writer.writeheader()
                logger.info(f"📊 Evaluation log created: {log_path}")
            writer.writerow(row)
            logger.info(
                f"📊 Eval logged | mode={effective_mode} | "
                f"latency={total_latency_ms}ms | chunks={len(results)}"
            )
    except Exception as e:
        # Never crash the chat endpoint because of logging failures
        logger.error(f"Evaluation logging failed (non-fatal): {e}")
