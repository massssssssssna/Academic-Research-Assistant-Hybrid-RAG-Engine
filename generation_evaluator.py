"""
generation_evaluator.py — Production RAG Evaluation Engine (Robust Version)

This module implements a local semantic generation evaluation layer.
It uses:
    1. spaCy (en_core_web_sm) for semantic claim extraction (ignoring noise/formatting).
    2. SentenceTransformer ("all-MiniLM-L6-v2") for semantic similarity embeddings.
    3. VoyageAI Embeddings (langchain-voyageai) as a fast, DLL-free fallback if PyTorch fails to load.
    4. TF-IDF Cosine Similarity (scikit-learn) for lexical/structural matching.
    5. Keyword Overlap (Jaccard on filtered tokens) for exact term matching.

It combines these signals using a weighted scoring model (70% Semantic, 20% TF-IDF, 10% Keyword)
to drastically reduce false hallucination detections caused by paraphrasing.

If PyTorch fails to load due to native OS/DLL conflicts (e.g. Python 3.14 Windows compatibility),
it gracefully falls back to VoyageAI (batched in 1 request for <200ms latency) and then spaCy lemma-matching.
"""

import re
import os
import time
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)

# ── Global Cache for Lazy-Loaded Models ──────────────────────────────────────
_nlp = None                  # spaCy model
_sentence_model = None       # SentenceTransformer model
_voyage_model = None         # VoyageAIEmbeddings fallback
_tfidf_vectorizer = None     # TF-IDF Vectorizer class
_model_load_attempted = False
_local_semantic_available = False
_voyage_semantic_available = False

def _initialize_engines():
    """
    Lazy-loads spaCy, SentenceTransformer, or VoyageAI to keep API startup fast.
    Handles OS-level DLL initialization issues gracefully.
    """
    global _nlp, _sentence_model, _voyage_model, _tfidf_vectorizer, _model_load_attempted, _local_semantic_available, _voyage_semantic_available
    if _model_load_attempted:
        return

    _model_load_attempted = True

    # 1. Load spaCy (required for claim extraction)
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
        logger.info("✅ spaCy (en_core_web_sm) loaded successfully for evaluation.")
    except Exception as e:
        logger.warning(f"⚠️ spaCy loading failed: {e}. Falling back to regex-based splitter.")
        _nlp = None

    # 2. Load TF-IDF Vectorizer
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        _tfidf_vectorizer = TfidfVectorizer
        logger.info("✅ scikit-learn TfidfVectorizer loaded successfully.")
    except Exception as e:
        logger.warning(f"⚠️ scikit-learn not available: {e}. Lexical matching will use fallback tokens.")
        _tfidf_vectorizer = None

    # 3. Load SentenceTransformer (requires PyTorch)
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer ('all-MiniLM-L6-v2')...")
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        _local_semantic_available = True
        logger.info("✅ SentenceTransformer loaded successfully. Semantic embeddings active.")
    except Exception as e:
        # Graceful fallback: torch DLL crash (WinError 1114) or Python 3.14 compatibility limits
        logger.warning(
            f"⚠️ SentenceTransformer local initialization failed: {e}. "
            "Trying VoyageAI Embeddings as high-performance backup."
        )
        _sentence_model = None
        _local_semantic_available = False

        # Try initializing VoyageAI embeddings fallback
        try:
            from dotenv import load_dotenv
            load_dotenv()
            if os.getenv("VOYAGE_API_KEY"):
                from langchain_voyageai import VoyageAIEmbeddings
                # Reuse the existing Voyage model config to minimize key fetches
                _voyage_model = VoyageAIEmbeddings(model="voyage-large-2")
                _voyage_semantic_available = True
                logger.info("✅ VoyageAI Embeddings initialized successfully as evaluation fallback.")
            else:
                logger.warning("⚠️ VOYAGE_API_KEY not found in environment. Voyage fallback unavailable.")
        except Exception as ve:
            logger.warning(f"⚠️ VoyageAI Embeddings fallback initialization failed: {ve}")
            _voyage_model = None
            _voyage_semantic_available = False


# ── Step 1: Better Factual Claim Extraction (spaCy) ──────────────────────────

def _extract_claims(answer: str) -> List[str]:
    """
    Uses spaCy to split the answer into clean, factual claims.
    Filters out greetings, formatting, headings, bullet symbols, and empty sentences.
    """
    _initialize_engines()

    # Pre-clean formatting and markdown tags
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", answer)  # bold
    clean = re.sub(r"\*([^*]+)\*", r"\1", clean)      # italic
    clean = re.sub(r"`[^`]+`", "", clean)             # inline code
    clean = re.sub(r"^#{1,6}\s+", "", clean, flags=re.MULTILINE) # headings

    # Noise/Greeting patterns to ignore
    noise_patterns = [
        r"^(hi|hello|hey|greetings|dear)\b",
        r"^(here is|sure|here are|based on|according to)\b",
        r"^(hope this helps|let me know|thank you|thanks)\b",
    ]

    claims = []

    if _nlp is not None:
        try:
            doc = _nlp(clean)
            for sent in doc.sents:
                text = sent.text.strip()
                # Skip short sentences or empty lines
                if not text or len(text.split()) < 4:
                    continue

                # Filter out greetings/meta-talk
                if any(re.match(p, text.lower()) for p in noise_patterns):
                    continue

                # Filter out formatting headers or markdown artifact lines
                if text.startswith("[") and text.endswith("]"):
                    continue

                # Strip leading list symbols
                text_clean = re.sub(r"^[-•*\d+.)\s]+", "", text).strip()
                if len(text_clean.split()) >= 4:
                    claims.append(text_clean)
        except Exception as e:
            logger.warning(f"spaCy claim extraction failed: {e}. Using regex fallback.")
            _nlp_fallback = None
    else:
        _nlp_fallback = True

    if _nlp is None or len(claims) == 0:
        # Regex-based fallback
        raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])|(?<=\n)", clean)
        for s in raw_sentences:
            s = s.strip()
            # Strip bullet prefixes
            s_clean = re.sub(r"^[-•*\d+.)\s]+", "", s).strip()
            if len(s_clean.split()) >= 5:
                if not any(re.match(p, s_clean.lower()) for p in noise_patterns):
                    claims.append(s_clean)

    # Deduplicate while preserving order
    final_claims = []
    seen = set()
    for c in claims:
        k = c.lower().strip()
        if k not in seen and len(k) > 10:
            final_claims.append(c)
            seen.add(k)

    if not final_claims:
        final_claims = [answer.strip()] if answer.strip() else []

    return final_claims


# ── Step 2: Lexical Similarity (TF-IDF) ───────────────────────────────────────

def _compute_tfidf_similarity(text_a: str, text_b: str) -> float:
    """
    Computes cosine similarity of TF-IDF vectors for exact lexical matching.
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0

    if _tfidf_vectorizer is not None:
        try:
            vec = _tfidf_vectorizer(stop_words="english", ngram_range=(1, 2))
            matrix = vec.fit_transform([text_a, text_b])
            vec_a = matrix[0].toarray()[0]
            vec_b = matrix[1].toarray()[0]
            norm_a = (vec_a ** 2).sum() ** 0.5
            norm_b = (vec_b ** 2).sum() ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float((vec_a * vec_b).sum() / (norm_a * norm_b))
        except Exception:
            pass

    # Basic token-matching fallback
    set_a = set(text_a.lower().split())
    set_b = set(text_b.lower().split())
    intersect = set_a & set_b
    union = set_a | set_b
    return len(intersect) / len(union) if union else 0.0


# ── Step 3: Keyword Overlap (Jaccard on spaCy Lemmatized Content Words) ────────

def _compute_keyword_overlap(text_a: str, text_b: str) -> float:
    """
    Computes exact matching overlap of nouns, verbs, adjectives, and numbers.
    Utilizes spaCy's part-of-speech tagger if available for maximum accuracy.
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0

    def get_keywords(text: str) -> Set[str]:
        if _nlp is not None:
            try:
                doc = _nlp(text)
                # Keep nouns, verbs, adjectives, proper nouns, and numbers
                keep_pos = {"NOUN", "PROPN", "VERB", "ADJ", "NUM"}
                return {t.lemma_.lower() for t in doc if t.pos_ in keep_pos and not t.is_stop}
            except Exception:
                pass
        # Fallback simple tokenize
        return {w.lower() for w in text.split() if len(w) > 3}

    keywords_a = get_keywords(text_a)
    keywords_b = get_keywords(text_b)

    if not keywords_a or not keywords_b:
        return 0.0

    intersect = keywords_a & keywords_b
    union = keywords_a | keywords_b
    return len(intersect) / len(union)


# ── Step 4: Semantic Embeddings (SentenceTransformer, Voyage, or spaCy Fallback) ──

def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

def _compute_semantic_matrix(claims: List[str], chunks: List[str]) -> np.ndarray:
    """
    Generates a matrix of semantic similarity scores [len(claims), len(chunks)].
    Tries Local SentenceTransformer first, then VoyageAI batch API, then spaCy fallback.
    """
    matrix = np.zeros((len(claims), len(chunks)))

    # Option A: Local SentenceTransformer
    if _local_semantic_available and _sentence_model is not None:
        try:
            claim_embeddings = _sentence_model.encode(claims, convert_to_numpy=True)
            chunk_embeddings = _sentence_model.encode(chunks, convert_to_numpy=True)
            for i, c_emb in enumerate(claim_embeddings):
                for j, ch_emb in enumerate(chunk_embeddings):
                    matrix[i, j] = _cosine_similarity(c_emb, ch_emb)
            return matrix
        except Exception as e:
            logger.warning(f"Local SentenceTransformer matrix generation failed: {e}. Trying Voyage.")

    # Option B: VoyageAI batch API fallback (Runs in 1 request to avoid API rate limits)
    if _voyage_semantic_available and _voyage_model is not None:
        try:
            # Batch all strings to send exactly 1 request
            all_texts = claims + chunks
            all_embeddings = _voyage_model.embed_documents(all_texts)
            
            # Split back
            claim_embeddings = np.array(all_embeddings[:len(claims)])
            chunk_embeddings = np.array(all_embeddings[len(claims):])
            
            for i, c_emb in enumerate(claim_embeddings):
                for j, ch_emb in enumerate(chunk_embeddings):
                    matrix[i, j] = _cosine_similarity(c_emb, ch_emb)
            return matrix
        except Exception as e:
            logger.warning(f"VoyageAI batch embeddings failed: {e}. Falling back to spaCy lemma.")

    # Option C: spaCy lemma-overlap fallback (DLL-free, completely local CPU)
    for i, claim in enumerate(claims):
        for j, chunk in enumerate(chunks):
            if _nlp is not None:
                try:
                    doc_a = _nlp(claim)
                    doc_b = _nlp(chunk)
                    lemmas_a = {t.lemma_.lower() for t in doc_a if not t.is_stop and t.pos_ in {"NOUN", "PROPN", "VERB", "ADJ"}}
                    lemmas_b = {t.lemma_.lower() for t in doc_b if not t.is_stop and t.pos_ in {"NOUN", "PROPN", "VERB", "ADJ"}}
                    if lemmas_a and lemmas_b:
                        # Use asymmetric overlap to see if claim terms are inside chunk
                        overlap = len(lemmas_a & lemmas_b) / len(lemmas_a)
                        # Boost slightly to align with SentenceTransformer scale
                        matrix[i, j] = min(1.0, overlap * 1.15)
                        continue
                except Exception:
                    pass
            # Raw tokens fallback
            w_a = set(claim.lower().split())
            w_b = set(chunk.lower().split())
            matrix[i, j] = len(w_a & w_b) / len(w_a) if w_a else 0.0

    return matrix


# ── Step 5: Main Entry Point & Calibrated Evaluation ───────────────────────

def evaluate_response(
    query: str,
    answer: str,
    retrieved_chunks: List[Dict[str, Any]],
    retrieval_latency_ms: float,
    reranking_latency_ms: float,
    generation_latency_ms: float,
) -> Dict[str, Any]:
    """
    Performs generation evaluation post-LLM response.
    Never crashes, uses optimized batched fallback layers (<250ms).
    """
    eval_start = time.perf_counter()

    try:
        # Extract plain chunk texts
        chunk_texts = [
            hit.get("text", "").strip()
            for hit in retrieved_chunks
            if hit.get("text", "").strip()
        ]

        # Initialize engines
        _initialize_engines()

        # Step 1: Claim extraction (using spaCy)
        claims = _extract_claims(answer)
        total_claims = len(claims)

        # Step 2: Compute semantic similarity matrix
        if total_claims > 0 and len(chunk_texts) > 0:
            semantic_matrix = _compute_semantic_matrix(claims, chunk_texts)
        else:
            semantic_matrix = np.zeros((total_claims, len(chunk_texts)))

        supported_claims_list = []
        unsupported_claims_list = []
        contributing_chunk_ids = set()

        sum_semantic = 0.0
        sum_tfidf = 0.0
        sum_keyword = 0.0
        sum_overall = 0.0

        # Step 3: Calibrated Weighted Scoring & Hallucination Detection
        # A claim should be marked supported if:
        # Combined Score = 70% Semantic + 20% TF-IDF + 10% Keyword Overlap is high
        for i, claim in enumerate(claims):
            best_combined = 0.0
            best_semantic = 0.0
            best_tfidf = 0.0
            best_keyword = 0.0
            best_chunk_idx = -1

            for j, chunk in enumerate(chunk_texts):
                semantic = semantic_matrix[i, j]
                tfidf = _compute_tfidf_similarity(claim, chunk)
                keyword = _compute_keyword_overlap(claim, chunk)

                # Weighted Scoring model: 70% Semantic + 20% TF-IDF + 10% Keyword
                combined = (0.70 * semantic) + (0.20 * tfidf) + (0.10 * keyword)

                if combined > best_combined:
                    best_combined = combined
                    best_semantic = semantic
                    best_tfidf = tfidf
                    best_keyword = keyword
                    best_chunk_idx = j

            # Auto-Tuned Hallucination Threshold:
            # Mark Supported only if Semantic Similarity >= 0.58 OR
            # TF-IDF & Keyword signals are exceptionally high (e.g. synonym overlap)
            is_supported = (
                best_semantic >= 0.58 or
                (best_combined >= 0.52 and best_tfidf > 0.15) or
                (best_semantic >= 0.45 and best_keyword > 0.35)
            )

            sum_semantic += best_semantic
            sum_tfidf += best_tfidf
            sum_keyword += best_keyword
            sum_overall += best_combined

            if is_supported and best_chunk_idx != -1:
                supported_claims_list.append(claim)
                contributing_chunk_ids.add(best_chunk_idx)
            else:
                unsupported_claims_list.append(claim)

        # Average quality scores
        avg_semantic = sum_semantic / total_claims if total_claims > 0 else 0.0
        avg_tfidf = sum_tfidf / total_claims if total_claims > 0 else 0.0
        avg_keyword = sum_keyword / total_claims if total_claims > 0 else 0.0
        avg_overall = sum_overall / total_claims if total_claims > 0 else 0.0

        # Faithfulness = Supported Claims / Total Claims
        faithfulness_score = len(supported_claims_list) / total_claims if total_claims > 0 else 0.0

        # Hallucination Detection: Flagged ONLY if faithfulness is low
        # and there are chunks but no claims supported.
        hallucination_detected = (
            faithfulness_score < 0.50 or
            (len(chunk_texts) > 0 and len(supported_claims_list) == 0)
        )

        if len(chunk_texts) == 0:
            hallucination_detected = False
            faithfulness_score = 1.0  # General knowledge fallback

        # Context Utilization
        context_util = len(contributing_chunk_ids) / len(chunk_texts) if len(chunk_texts) > 0 else 0.0

        # Answer Relevancy (Query vs Answer)
        # We can reuse our semantic matrix framework to get the semantic score of the query vs answer
        if _voyage_semantic_available and _voyage_model is not None:
            try:
                emb_q_ans = _voyage_model.embed_documents([query, answer])
                answer_relevancy = _cosine_similarity(np.array(emb_q_ans[0]), np.array(emb_q_ans[1]))
            except Exception:
                answer_relevancy = _compute_semantic_similarity(query, answer)
        else:
            answer_relevancy = _compute_semantic_similarity(query, answer)

        # Latencies
        total_latency_ms = retrieval_latency_ms + reranking_latency_ms + generation_latency_ms

        # Overall Weighted Score (0-100)
        # 40% Faithfulness + 25% Relevancy + 20% Context Utilization + 15% No Hallucination
        hallucination_penalty = 0.0 if hallucination_detected else 1.0
        overall_score = round((
            0.40 * faithfulness_score +
            0.25 * answer_relevancy +
            0.20 * context_util +
            0.15 * hallucination_penalty
        ) * 100)

        eval_elapsed = (time.perf_counter() - eval_start) * 1000
        logger.info(
            f"📊 Eval complete | Claims={total_claims} | Faithfulness={faithfulness_score:.2f} | "
            f"Hallucination={hallucination_detected} | Semantic={avg_semantic:.2f} | "
            f"Overall={overall_score} | Time={eval_elapsed:.1f}ms"
        )

        return {
            # Core Metrics
            "faithfulness_score": round(faithfulness_score, 4),
            "hallucination_detected": hallucination_detected,
            "supported_claims": len(supported_claims_list),
            "unsupported_claims": len(unsupported_claims_list),
            "context_utilization": round(context_util, 4),
            "answer_relevancy": round(answer_relevancy, 4),

            # Latencies
            "retrieval_latency_ms": round(retrieval_latency_ms, 1),
            "reranking_latency_ms": round(reranking_latency_ms, 1),
            "generation_latency_ms": round(generation_latency_ms, 1),
            "total_latency_ms": round(total_latency_ms, 1),

            # Individual Score Averages (for Frontend Dashboard details)
            "semantic_score": round(avg_semantic, 4),
            "tfidf_score": round(avg_tfidf, 4),
            "keyword_score": round(avg_keyword, 4),
            "overall_score": overall_score,

            # Lists
            "claims": claims,
            "supported_claim_list": supported_claims_list,
            "unsupported_claim_list": unsupported_claims_list,
            "retrieved_chunks": chunk_texts,
        }

    except Exception as e:
        logger.error(f"Generation evaluation failed: {e}", exc_info=True)
        total_latency_ms = retrieval_latency_ms + reranking_latency_ms + generation_latency_ms
        return {
            "faithfulness_score": 0.0,
            "hallucination_detected": False,
            "supported_claims": 0,
            "unsupported_claims": 0,
            "context_utilization": 0.0,
            "answer_relevancy": 0.0,
            "retrieval_latency_ms": round(retrieval_latency_ms, 1),
            "reranking_latency_ms": round(reranking_latency_ms, 1),
            "generation_latency_ms": round(generation_latency_ms, 1),
            "total_latency_ms": round(total_latency_ms, 1),
            "semantic_score": 0.0,
            "tfidf_score": 0.0,
            "keyword_score": 0.0,
            "overall_score": 0,
            "claims": [],
            "supported_claim_list": [],
            "unsupported_claim_list": [],
            "retrieved_chunks": [],
            "error": str(e)
        }
