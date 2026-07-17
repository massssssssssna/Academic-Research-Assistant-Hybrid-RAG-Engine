"""
ingest_folder.py — Bulk Local Folder Ingestion Utility.

Reads all PDF and TXT files from a local folder and ingests them into Qdrant.
Useful for pre-loading a collection before running evaluation experiments.

All parameters (chunk_size, overlap, batch_size, sleep intervals) are
read from Config — no hardcoded values.

Usage:
    python ingest_folder.py              (uses default folder: Data/)
    python ingest_folder.py my_papers/   (specify a custom folder)
"""

import os
import glob
import time
import uuid
import logging
import sys
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct

from config import Config
from data_ingestion import voyage_embeddings, qdrant_client, COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP, BATCH_SIZE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def ingest_local_folder(folder_path: str = "Data") -> None:
    """
    Discovers and ingests all PDF and TXT files in the given folder into Qdrant.

    For each file:
        1. Extract text (pypdf for PDFs, plain read for TXT).
        2. Chunk with RecursiveCharacterTextSplitter using Config values.
        3. Embed with Voyage AI in batches (with rate-limit retry).
        4. Upsert points to Qdrant.

    Args:
        folder_path: Path to the folder containing PDF/TXT files.
                     Created automatically if it doesn't exist.
    """
    # ── Ensure folder exists ──────────────────────────────────────────────────
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger.info(
            f"Created folder '{folder_path}'. "
            f"Add your PDF/TXT files there and run this script again."
        )
        return

    # ── Discover files ────────────────────────────────────────────────────────
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    all_files = pdf_files + txt_files

    if not all_files:
        logger.warning(f"No PDF or TXT files found in '{folder_path}'.")
        return

    logger.info(f"Found {len(all_files)} files | chunk_size={CHUNK_SIZE} | "
                f"overlap={CHUNK_OVERLAP} | batch={BATCH_SIZE}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    total_uploaded = 0

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        logger.info(f"Processing: {file_name}")

        try:
            # ── Extract text ──────────────────────────────────────────────────
            full_text = ""
            if file_path.lower().endswith(".pdf"):
                pdf_reader = PdfReader(file_path)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            elif file_path.lower().endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    full_text = f.read()

            if not full_text.strip():
                logger.warning(f"No text extracted from {file_name}. Skipping.")
                continue

            # ── Chunk ─────────────────────────────────────────────────────────
            chunks = text_splitter.create_documents([full_text])
            logger.info(f"Generated {len(chunks)} chunks for {file_name}.")

            # ── Embed and upsert in batches ───────────────────────────────────
            num_batches = (len(chunks) - 1) // BATCH_SIZE + 1
            for i in range(0, len(chunks), BATCH_SIZE):
                batch_texts = [c.page_content for c in chunks[i:i + BATCH_SIZE]]
                batch_num   = i // BATCH_SIZE + 1

                # Embedding with retry
                for attempt in range(3):
                    try:
                        embeddings = voyage_embeddings.embed_documents(batch_texts)
                        break
                    except Exception as embed_err:
                        err_str = str(embed_err).lower()
                        if "rate limit" in err_str or "payment" in err_str:
                            wait = 65 if attempt == 0 else 30
                            logger.warning(f"Rate limit hit. Waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            raise embed_err
                else:
                    logger.error(f"Embedding failed for batch {batch_num} of {file_name}. Skipping batch.")
                    continue

                # Build Qdrant points
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
                                "chunk_id": global_idx,
                            }
                        )
                    )

                qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
                logger.info(f"Uploaded batch {batch_num}/{num_batches} for {file_name}")

                # Rate-limit sleep
                if i + BATCH_SIZE < len(chunks):
                    time.sleep(Config.INGEST_BATCH_SLEEP_S)

            total_uploaded += len(chunks)

        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}")

    logger.info(f"✅ Folder ingestion complete. Total chunks indexed: {total_uploaded}")


if __name__ == "__main__":
    # Allow custom folder path as CLI argument
    folder = sys.argv[1] if len(sys.argv) > 1 else "Data"
    ingest_local_folder(folder)
