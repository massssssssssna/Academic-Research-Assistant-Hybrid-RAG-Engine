"""
data_ingestion.py — PDF Upload & Indexing Pipeline.

Handles ingestion of a single PDF uploaded via the /api/upload endpoint.
All chunking parameters (chunk_size, overlap, batch_size) are read from
Config so they can be changed without touching this file.

Pipeline:
    PDF bytes → text extraction (pypdf)
             → chunking (RecursiveCharacterTextSplitter)
             → embedding (Voyage AI voyage-3)
             → vector upsert (Qdrant Cloud)

Rate limit handling:
    Voyage AI free tier allows 3 RPM / 10k TPM.
    Batches of INGEST_BATCH_SIZE chunks are uploaded with a sleep of
    INGEST_BATCH_SLEEP_S seconds between batches to stay within limits.
"""

import os
import io
import uuid
import time
import logging
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from config import Config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── All parameters now come from Config ──────────────────────────────────────
COLLECTION_NAME = Config.COLLECTION_NAME
CHUNK_SIZE      = Config.CHUNK_SIZE
CHUNK_OVERLAP   = Config.CHUNK_OVERLAP
BATCH_SIZE      = Config.INGEST_BATCH_SIZE
EMBEDDING_MODEL = Config.EMBEDDING_MODEL
VECTOR_SIZE     = Config.VECTOR_SIZE

# ── Initialize shared clients ─────────────────────────────────────────────────
voyage_embeddings = VoyageAIEmbeddings(
    voyage_api_key=Config.VOYAGE_API_KEY,
    model=EMBEDDING_MODEL
)

qdrant_client = QdrantClient(
    url=Config.QDRANT_CLUSTER_URL,
    api_key=Config.QDRANT_API_KEY,
    timeout=30
)


def process_and_index_pdf(file_bytes: bytes, file_name: str) -> int:
    """
    Ingests a single PDF from raw bytes into Qdrant.

    Steps:
        1. Ensure the Qdrant collection exists (creates if missing).
        2. Extract text from all PDF pages using pypdf.
        3. Split text into overlapping chunks using RecursiveCharacterTextSplitter.
        4. Embed each batch of chunks with Voyage AI (with rate-limit retry).
        5. Upsert each batch of vectors + payloads into Qdrant.

    Args:
        file_bytes: Raw PDF file content as bytes.
        file_name:  Original filename (used as the 'source' metadata field).

    Returns:
        Total number of chunks indexed. Returns 0 on any error.

    NOTE: This function is called as a FastAPI BackgroundTask. Any uncaught
    exception here propagates through Starlette and causes a 500 response to
    the client even though the upload already returned 200. Therefore the
    entire body is wrapped in a top-level try-except that logs and returns 0
    on failure instead of raising.
    """
    try:
        return _process_and_index_pdf_inner(file_bytes, file_name)
    except Exception as e:
        logger.error(f"Background PDF indexing failed for '{file_name}': {e}", exc_info=True)
        return 0


def _process_and_index_pdf_inner(file_bytes: bytes, file_name: str) -> int:
    """
    Inner implementation of process_and_index_pdf.
    Called by the public wrapper which catches all exceptions.
    """
    logger.info(f"Processing uploaded PDF: {file_name}")
    logger.info(f"Config | chunk_size={CHUNK_SIZE} | overlap={CHUNK_OVERLAP} | "
                f"batch={BATCH_SIZE} | embed_model={EMBEDDING_MODEL}")

    # ── Step 1: Ensure collection exists ────────────────────────────────────
    logger.info(f"Ensuring Qdrant collection '{COLLECTION_NAME}' exists...")
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            on_disk_payload=True
        )
        logger.info(f"Created new collection '{COLLECTION_NAME}'.")

    # ── Step 2: Extract text from PDF ───────────────────────────────────────
    # strict=False tolerates malformed/truncated PDFs that pypdf
    # would otherwise reject with PdfStreamError.
    pdf_reader = PdfReader(io.BytesIO(file_bytes), strict=False)
    full_text = ""
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    if not full_text.strip():
        logger.warning(f"No text extracted from {file_name}. Skipping.")
        return 0

    # ── Step 3: Split into chunks ──────────────────────────────────────────────
    logger.info(f"Splitting text | chunk_size={CHUNK_SIZE} | overlap={CHUNK_OVERLAP}")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = text_splitter.create_documents([full_text])
    total_chunks = len(chunks)
    logger.info(f"Generated {total_chunks} chunks.")

    # ── Step 4 & 5: Embed and upload in batches ────────────────────────────────
    logger.info("Embedding and uploading chunks to Qdrant...")

    num_batches = (total_chunks - 1) // BATCH_SIZE + 1
    for i in range(0, total_chunks, BATCH_SIZE):
        batch_texts = [c.page_content for c in chunks[i:i + BATCH_SIZE]]
        batch_num   = i // BATCH_SIZE + 1

        # ── Embedding with rate-limit retry ─────────────────────────────────
        for attempt in range(3):
            try:
                embeddings = voyage_embeddings.embed_documents(batch_texts)
                break
            except Exception as embed_err:
                err_str = str(embed_err).lower()
                if "rate limit" in err_str or "payment method" in err_str:
                    wait = 62 if attempt == 0 else 30
                    logger.warning(f"Voyage rate limit hit (attempt {attempt + 1}). "
                                   f"Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Embedding API failed: {embed_err}") from embed_err
        else:
            raise RuntimeError("Voyage AI embedding failed after 3 retries.")

        # ── Build Qdrant point structs ────────────────────────────────────────
        points = []
        for j, chunk_text in enumerate(batch_texts):
            global_idx = i + j
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embeddings[j],
                    payload={
                        "text":     chunk_text,
                        "source":   file_name,
                        "chunk_id": global_idx,     # sequential integer ID for evaluation
                    }
                )
            )

        # ── Upload batch to Qdrant ────────────────────────────────────────────
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"Uploaded batch {batch_num}/{num_batches} to Qdrant.")

        # ── Rate-limit sleep between batches ──────────────────────────────────
        if i + BATCH_SIZE < total_chunks:
            time.sleep(Config.INGEST_BATCH_SLEEP_S)

    logger.info(f"✅ Finished indexing '{file_name}' → {total_chunks} chunks in Qdrant.")
    return total_chunks
