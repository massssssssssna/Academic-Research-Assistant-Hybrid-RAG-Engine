"""
reranker.py — Cross-Encoder Reranker Module.

Re-scores a candidate list of (query, passage) pairs and returns them
sorted by relevance. This module supports two backends, tried in order:

    1. ONNX Runtime (via optimum + onnxruntime) — recommended, works on Python 3.14+,
       no GPU needed, ~80MB model download.
    2. sentence-transformers / PyTorch — fallback if ONNX backend unavailable.
       Requires PyTorch which must be compatible with the system Python version.

If neither backend is available, a graceful BM25-score-based ranking is used
so that the overall retrieval pipeline does not crash.

Why a cross-encoder?
    Bi-encoders (Voyage AI) encode query and document independently.
    This is fast but misses fine-grained query-document interactions.
    A cross-encoder processes the concatenation [query, document] through
    a full attention mechanism, producing far more accurate relevance scores.
    Used only on a small candidate pool (e.g., top-50) to balance
    accuracy and latency.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
    Trained on MS MARCO passage ranking — standard academic benchmark model.
    No API key required. Downloads once, then cached locally.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Module-level singleton — lazy loaded on first call to rerank()
_reranker_model = None
_backend_used = None   # "onnx" | "sentence_transformers" | "fallback"


def _try_load_onnx_backend():
    """
    Attempts to load the cross-encoder via optimum's ONNX Runtime backend.
    This works on Python 3.14+ where PyTorch DLLs may fail to load.

    Returns:
        A callable predict(pairs) -> list[float], or None on failure.
    """
    try:
        from optimum.onnxruntime import ORTModelForSequenceClassification
        from transformers import AutoTokenizer

        logger.info("Loading CrossEncoder via ONNX Runtime backend...")
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = ORTModelForSequenceClassification.from_pretrained(
            model_name,
            export=True,
            provider="CPUExecutionProvider",
        )

        def predict(pairs: List[tuple]) -> List[float]:
            inputs = tokenizer(
                [p[0] for p in pairs],
                [p[1] for p in pairs],
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt",
            )
            outputs = model(**inputs)
            logits = outputs.logits.detach().numpy()
            if logits.shape[-1] > 1:
                scores = logits[:, 1].tolist()
            else:
                scores = logits[:, 0].tolist()
            return scores

        logger.info("✅ CrossEncoder loaded via ONNX Runtime.")
        return predict

    except Exception as e:
        logger.warning(f"ONNX backend failed: {e}. Trying sentence-transformers...")
        return None


def _try_load_st_backend():
    """
    Attempts to load the cross-encoder via sentence-transformers (PyTorch).
    May fail on Python 3.14 if PyTorch DLLs are incompatible.

    Returns:
        A callable predict(pairs) -> list[float], or None on failure.
    """
    try:
        from sentence_transformers import CrossEncoder
        logger.info("Loading CrossEncoder via sentence-transformers backend...")
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)

        def predict(pairs: List[tuple]) -> List[float]:
            scores = model.predict(pairs)
            return [float(s) for s in scores]

        logger.info("✅ CrossEncoder loaded via sentence-transformers.")
        return predict

    except Exception as e:
        logger.warning(f"sentence-transformers backend failed: {e}. Using fallback scorer.")
        return None


def _load_reranker():
    """
    Loads the best available reranker backend.
    Tries: ONNX → sentence-transformers → fallback (graceful degradation).
    Result is cached in module-level singleton after first call.

    Returns:
        Tuple of (predict_fn, backend_name_str).
    """
    global _reranker_model, _backend_used

    if _reranker_model is not None:
        return _reranker_model, _backend_used

    # Try ONNX first (Python 3.14 compatible)
    predict_fn = _try_load_onnx_backend()
    if predict_fn:
        _reranker_model = predict_fn
        _backend_used = "onnx"
        return _reranker_model, _backend_used

    # Fall back to sentence-transformers (requires working PyTorch)
    predict_fn = _try_load_st_backend()
    if predict_fn:
        _reranker_model = predict_fn
        _backend_used = "sentence_transformers"
        return _reranker_model, _backend_used

    # Ultimate fallback — no neural reranking, sort by existing BM25/RRF score
    logger.warning(
        "⚠️ No reranker backend available. "
        "hybrid_rerank will fall back to RRF ordering. "
        "To fix on Python 3.14: install optimum[onnxruntime]."
    )
    _backend_used = "fallback"
    _reranker_model = None
    return None, "fallback"


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Re-ranks a list of candidate chunks using the best available CrossEncoder backend.

    Args:
        query:      The user's search query string.
        candidates: List of result dicts, each must have a 'text' key.
                    May also have 'rrf_score', 'bm25_score', 'score', etc.
        top_k:      Number of top results to return after reranking.

    Returns:
        Top_k candidate dicts sorted by rerank_score descending.
        Each dict retains all original fields plus a 'rerank_score' key.
        If no neural backend is available, returns top_k candidates
        sorted by existing score (graceful degradation).

    Example:
        reranked = rerank(
            query="What is the main contribution?",
            candidates=[{"text": "This paper proposes...", "source": "paper.pdf"}, ...],
            top_k=5
        )
    """
    if not candidates:
        return []

    top_k = min(top_k, len(candidates))

    predict_fn, backend = _load_reranker()

    # ── Graceful fallback: no neural backend available ────────────────────────
    if predict_fn is None:
        logger.warning("Reranker unavailable — returning candidates sorted by RRF/BM25 score.")
        candidates_sorted = sorted(
            candidates,
            key=lambda x: x.get("rrf_score", x.get("bm25_score", x.get("score", 0.0))),
            reverse=True
        )
        for c in candidates_sorted:
            c["rerank_score"] = c.get("rrf_score", 0.0)
        return candidates_sorted[:top_k]

    # ── Neural reranking ──────────────────────────────────────────────────────
    pairs = [(query, c.get("text", "")) for c in candidates]

    logger.info(f"Reranking {len(pairs)} candidates with CrossEncoder [{backend}]...")
    try:
        scores = predict_fn(pairs)
    except Exception as e:
        logger.error(f"Reranker inference failed: {e}. Falling back to RRF order.")
        for c in candidates:
            c["rerank_score"] = c.get("rrf_score", 0.0)
        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]

    # Attach scores and sort descending
    scored = []
    for i, candidate in enumerate(candidates):
        scored.append({**candidate, "rerank_score": float(scores[i])})

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)

    logger.info(
        f"Reranking complete [{backend}] | "
        f"top_score={scored[0]['rerank_score']:.4f} | "
        f"returning top {top_k}"
    )
    return scored[:top_k]
