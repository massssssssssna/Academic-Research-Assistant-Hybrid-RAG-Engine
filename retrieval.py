"""
retrieval.py — Unified Retrieval Strategy Router.

Supports three retrieval strategies, configurable via Config.RETRIEVAL_MODE:

    dense          → Voyage AI embeddings + Qdrant ANN cosine search
    hybrid         → Dense + BM25 fused with Reciprocal Rank Fusion (RRF)
    hybrid_rerank  → Hybrid (large pool) → CrossEncoder reranker → top_k

Why separate retrieval modes?
    Dense retrieval excels at semantic similarity — understanding meaning.
    BM25 excels at exact keyword matching — catching specific terms.
    Hybrid (RRF fusion) combines both strengths, consistently outperforming
    either approach alone on real-world RAG benchmarks.
    The cross-encoder reranker adds a final precision pass on the merged pool.

Reciprocal Rank Fusion (RRF):
    score(d) = Σ 1 / (k + rank(d))   where k=60 (Cormack et al., 2009)
    RRF is parameter-light and outperforms linear score interpolation.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from langchain_voyageai import VoyageAIEmbeddings

from config import Config

logger = logging.getLogger(__name__)

# Standard RRF constant from literature
RRF_K = 60


def _embed_query(voyage_embeddings: VoyageAIEmbeddings, query: str, max_retries: int = 3) -> list:
    """
    Embeds a query string using Voyage AI with retry on rate-limit errors.

    Args:
        voyage_embeddings: Initialized VoyageAIEmbeddings instance.
        query:             Raw query string.
        max_retries:       Number of retry attempts before raising.

    Returns:
        List of floats — 1024-dim query embedding vector.
    """
    for attempt in range(max_retries):
        try:
            return voyage_embeddings.embed_query(query)
        except Exception as e:
            err = str(e).lower()
            if "rate limit" in err or "payment" in err:
                wait = 65 if attempt == 0 else 30
                logger.warning(f"Voyage rate limit (attempt {attempt+1}). Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e
    raise RuntimeError("Voyage AI embedding failed after all retries.")


def _dense_search(
    qdrant_client: QdrantClient,
    voyage_embeddings: VoyageAIEmbeddings,
    query: str,
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Pure dense retrieval: embed the query and search Qdrant by cosine similarity.

    Args:
        qdrant_client:    Initialized QdrantClient.
        voyage_embeddings: Initialized VoyageAIEmbeddings.
        query:            User query string.
        top_k:            Number of results to return.

    Returns:
        List of dicts with keys: id, text, source, chunk_id, score.
    """
    qvec = _embed_query(voyage_embeddings, query)
    res = qdrant_client.query_points(
        collection_name=Config.COLLECTION_NAME,
        query=qvec,
        limit=top_k,
        with_payload=True
    )
    results = []
    for point in (res.points or []):
        payload = point.payload or {}
        text = (
            payload.get("text") or
            payload.get("page_content") or
            payload.get("content") or ""
        ).strip()
        results.append({
            "id":       str(point.id),
            "text":     text,
            "source":   payload.get("source") or payload.get("source_file_name") or "document",
            "chunk_id": payload.get("chunk_id", -1),
            "score":    point.score if hasattr(point, "score") else 0.0,
        })
    return results


def _fetch_bm25_corpus(qdrant_client: QdrantClient) -> List[Dict[str, Any]]:
    """
    Fetches all stored chunks from Qdrant to build the BM25 in-memory index.

    BM25 runs locally on this corpus. For academic-scale corpora
    (< 2000 chunks per paper), this is fast and accurate.

    Args:
        qdrant_client: Initialized QdrantClient.

    Returns:
        List of dicts with keys: id, text, source, chunk_id.
    """
    scroll_res, _ = qdrant_client.scroll(
        collection_name=Config.COLLECTION_NAME,
        limit=Config.BM25_CORPUS_LIMIT,
        with_payload=True,
        with_vectors=False
    )
    corpus = []
    for point in (scroll_res or []):
        payload = point.payload or {}
        text = (
            payload.get("text") or
            payload.get("page_content") or
            payload.get("content") or ""
        ).strip()
        if text:
            corpus.append({
                "id":       str(point.id),
                "text":     text,
                "source":   payload.get("source") or "document",
                "chunk_id": payload.get("chunk_id", -1),
            })
    return corpus


def _bm25_search(corpus: List[Dict[str, Any]], query: str, top_k: int) -> List[Dict[str, Any]]:
    """
    Runs BM25Okapi on the in-memory corpus and returns top_k results.

    BM25 (Best Match 25) is a probabilistic term-frequency model that
    excels at exact keyword matching — complementary to dense semantic search.

    Args:
        corpus: List of docs from _fetch_bm25_corpus().
        query:  Raw query string (tokenized by whitespace).
        top_k:  Number of results to return.

    Returns:
        List of dicts with 'bm25_score' field added.
    """
    from rank_bm25 import BM25Okapi

    if not corpus:
        return []

    # Tokenize: lowercase + whitespace split
    tokenized_corpus = [doc["text"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Sort descending by BM25 score
    scored = sorted(
        [(corpus[i], float(scores[i])) for i in range(len(corpus))],
        key=lambda x: x[1],
        reverse=True
    )

    return [{**doc, "bm25_score": score} for doc, score in scored[:top_k]]


def _reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Merges multiple ranked lists using Reciprocal Rank Fusion (RRF).

    Formula: score(d) = Σ_r [ 1 / (RRF_K + rank_r(d)) ]

    Args:
        ranked_lists: List of ranked result lists (e.g. [dense_results, bm25_results]).
        top_k:        Number of merged results to return.

    Returns:
        Top_k results sorted by RRF score descending, with 'rrf_score' field added.
    """
    rrf_scores: Dict[str, float] = {}
    doc_map:    Dict[str, Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        for rank_idx, doc in enumerate(ranked_list):
            doc_id = doc["id"]
            rank   = rank_idx + 1  # 1-indexed
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    return [
        {**doc_map[doc_id], "rrf_score": rrf_scores[doc_id]}
        for doc_id in sorted_ids[:top_k]
    ]


def retrieve(
    query: str,
    qdrant_client: QdrantClient,
    voyage_embeddings: VoyageAIEmbeddings,
    top_k: Optional[int] = None,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main retrieval entry point. Dispatches to dense or hybrid strategy.

    Args:
        query:             User query string.
        qdrant_client:     Initialized QdrantClient.
        voyage_embeddings: Initialized VoyageAIEmbeddings.
        top_k:             Number of results. Defaults to Config.TOP_K.
        mode:              'dense' or 'hybrid'. Defaults to Config.RETRIEVAL_MODE.

    Returns:
        Dict with keys:
            results         → List of result dicts (id, text, source, chunk_id, ...)
            retrieval_mode  → Mode actually used
            top_k           → top_k value used
            latency_ms      → Retrieval wall-clock time in milliseconds
    """
    effective_top_k = top_k if top_k is not None else Config.TOP_K
    effective_mode  = mode  if mode  is not None else Config.RETRIEVAL_MODE

    logger.info(f"Retrieval | mode={effective_mode} | top_k={effective_top_k} | query='{query[:60]}'")
    t0 = time.perf_counter()

    results: List[Dict[str, Any]] = []
    reranking_ms = 0.0

    # ── Dense Mode ──────────────────────────────────────────────────────────
    if effective_mode == "dense":
        results = _dense_search(qdrant_client, voyage_embeddings, query, effective_top_k)

    # ── Hybrid Mode (Dense + BM25 + RRF) ────────────────────────────────────
    elif effective_mode == "hybrid":
        corpus        = _fetch_bm25_corpus(qdrant_client)
        dense_results = _dense_search(qdrant_client, voyage_embeddings, query, effective_top_k * 3)
        bm25_results  = _bm25_search(corpus, query, effective_top_k * 3)
        results       = _reciprocal_rank_fusion([dense_results, bm25_results], effective_top_k)

    # ── Hybrid + Rerank Mode ─────────────────────────────────────────────────
    elif effective_mode == "hybrid_rerank":
        from reranker import rerank as cross_encoder_rerank

        # Step 1: Large candidate pool via hybrid
        pool_size     = max(Config.RERANK_TOP_N, effective_top_k * 5)
        corpus        = _fetch_bm25_corpus(qdrant_client)
        dense_results = _dense_search(qdrant_client, voyage_embeddings, query, pool_size)
        bm25_results  = _bm25_search(corpus, query, pool_size)
        candidates    = _reciprocal_rank_fusion([dense_results, bm25_results], pool_size)

        # Measure reranking latency separately so the dashboard can show it
        rerank_t0 = time.perf_counter()
        # Step 2: Rerank with CrossEncoder → trim to top_k
        # reranker.py has graceful fallback if neural backend unavailable
        results = cross_encoder_rerank(query, candidates, top_k=effective_top_k)
        reranking_ms = (time.perf_counter() - rerank_t0) * 1000
        logger.info(f"Reranking took {reranking_ms:.1f}ms")

    else:
        raise ValueError(
            f"Unknown retrieval mode: '{effective_mode}'. "
            f"Must be: dense | hybrid | hybrid_rerank"
        )

    latency_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Retrieval complete | {len(results)} results | {latency_ms:.1f}ms")

    # retrieval_only_ms excludes reranking so each stage can be displayed separately
    retrieval_only_ms = latency_ms - reranking_ms if effective_mode == "hybrid_rerank" else latency_ms

    return {
        "results":           results,
        "retrieval_mode":    effective_mode,
        "top_k":             effective_top_k,
        "latency_ms":        round(latency_ms, 2),
        "retrieval_only_ms": round(max(retrieval_only_ms, 0.0), 2),
        "reranking_ms":      round(reranking_ms, 2),
    }


def fallback_scroll(qdrant_client: QdrantClient, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Emergency fallback when all retrieval calls fail.
    Returns the first `limit` chunks via Qdrant scroll so the LLM
    always has some context rather than answering blind.

    Args:
        qdrant_client: Initialized QdrantClient.
        limit:         Number of chunks to fetch.

    Returns:
        List of result dicts (same schema as retrieve()).
    """
    try:
        scroll_res, _ = qdrant_client.scroll(
            collection_name=Config.COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        results = []
        for point in (scroll_res or []):
            payload = point.payload or {}
            text = (
                payload.get("text") or
                payload.get("page_content") or
                payload.get("content") or ""
            ).strip()
            results.append({
                "id":       str(point.id),
                "text":     text,
                "source":   payload.get("source") or "document",
                "chunk_id": payload.get("chunk_id", -1),
                "score":    0.0,
            })
        return results
    except Exception as e:
        logger.error(f"Fallback scroll also failed: {e}")
        return []
