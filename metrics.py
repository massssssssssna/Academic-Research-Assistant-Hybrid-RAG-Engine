"""
metrics.py — Offline Evaluation Metrics Calculator.

Reads a golden dataset (ground-truth query → relevant chunk_ids) and
a per-query evaluation log CSV (produced by evaluation.py), then computes
standard IR metrics used in RAG benchmarking research:

    Precision@K   — Of the K retrieved chunks, what fraction are relevant?
    Recall@K      — Of all relevant chunks, what fraction were retrieved in top K?
    MRR           — Mean Reciprocal Rank of the first relevant chunk
    nDCG@K        — Normalized Discounted Cumulative Gain (quality of ranking)
    Hit Rate@K    — % of queries where at least 1 relevant chunk was retrieved

Usage:
    python metrics.py --mode dense --log evaluation/dense_log.csv \
                      --golden golden_dataset.json [--k 6]

    python metrics.py --all   (processes all *_log.csv files and writes summary.csv)

Output:
    evaluation/summary.csv   — one row per mode with all metrics side by side
"""

import os
import csv
import json
import math
import argparse
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

EVAL_DIR = os.path.join(os.path.dirname(__file__), "evaluation")
SUMMARY_PATH = os.path.join(EVAL_DIR, "summary.csv")

SUMMARY_FIELDNAMES = [
    "Retrieval Mode",
    "Precision@K",
    "Recall@K",
    "MRR",
    "nDCG",
    "Hit Rate",
    "Average Retrieval Latency (ms)",
    "Average Generation Latency (ms)",
    "Average Total Latency (ms)",
    "TopK",
    "Chunk Size",
    "Chunk Overlap",
    "Number of Queries"
]


# ── Individual Metric Functions ────────────────────────────────────────────────

def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    Precision@K: fraction of the top-K retrieved items that are relevant.

    Formula: |retrieved[:k] ∩ relevant| / k

    Args:
        retrieved: Ordered list of retrieved chunk_ids (strings).
        relevant:  List of ground-truth relevant chunk_ids.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1].
    """
    if k == 0 or not retrieved:
        return 0.0
    relevant_set = set(str(r) for r in relevant)
    hits = sum(1 for doc_id in retrieved[:k] if str(doc_id) in relevant_set)
    return hits / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    Recall@K: fraction of all relevant items that appear in the top-K.

    Formula: |retrieved[:k] ∩ relevant| / |relevant|

    Args:
        retrieved: Ordered list of retrieved chunk_ids.
        relevant:  Ground-truth relevant chunk_ids.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1]. Returns 0.0 if relevant is empty.
    """
    if not relevant or not retrieved:
        return 0.0
    relevant_set = set(str(r) for r in relevant)
    hits = sum(1 for doc_id in retrieved[:k] if str(doc_id) in relevant_set)
    return hits / len(relevant_set)


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """
    MRR: reciprocal of the rank of the first relevant item.

    Formula: 1 / rank_of_first_relevant_item
    Returns 0.0 if no relevant item is retrieved.

    Args:
        retrieved: Ordered list of retrieved chunk_ids (first = rank 1).
        relevant:  Ground-truth relevant chunk_ids.

    Returns:
        Float in [0, 1].
    """
    relevant_set = set(str(r) for r in relevant)
    for rank, doc_id in enumerate(retrieved, start=1):
        if str(doc_id) in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    nDCG@K: Normalized Discounted Cumulative Gain using binary relevance.

    DCG@K  = Σ_{i=1}^{K}  rel_i / log2(i + 1)
    IDCG@K = Σ_{i=1}^{min(|relevant|,K)}  1 / log2(i + 1)
    nDCG@K = DCG@K / IDCG@K

    Binary relevance: rel_i = 1 if retrieved[i] is relevant, else 0.

    Args:
        retrieved: Ordered list of retrieved chunk_ids.
        relevant:  Ground-truth relevant chunk_ids.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1]. Returns 0.0 if relevant is empty or IDCG=0.
    """
    if not relevant or not retrieved:
        return 0.0

    relevant_set = set(str(r) for r in relevant)

    # DCG: actual gain from retrieved list
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k], start=1):
        rel = 1.0 if str(doc_id) in relevant_set else 0.0
        dcg += rel / math.log2(i + 1)

    # IDCG: ideal gain if we had retrieved all relevant items at the top
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

    if idcg == 0:
        return 0.0
    return dcg / idcg


def hit_rate_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """
    Hit Rate@K (also called Recall@1-hit): 1 if any relevant item is in top-K, else 0.

    This is the most lenient metric — it rewards any retrieval of a relevant chunk.
    Useful for measuring whether the LLM will have *any* relevant context to answer from.

    Args:
        retrieved: Ordered list of retrieved chunk_ids.
        relevant:  Ground-truth relevant chunk_ids.
        k:         Cutoff rank.

    Returns:
        1.0 if hit, 0.0 otherwise.
    """
    relevant_set = set(str(r) for r in relevant)
    return 1.0 if any(str(doc_id) in relevant_set for doc_id in retrieved[:k]) else 0.0


# ── Log File Reader ────────────────────────────────────────────────────────────

def load_log(log_path: str) -> List[Dict[str, Any]]:
    """
    Reads an evaluation CSV log produced by evaluation.py.

    Args:
        log_path: Path to the *_log.csv file.

    Returns:
        List of row dicts. The 'retrieved_chunk_ids' field is parsed
        from a pipe-separated string into a list of strings.
    """
    rows = []
    if not os.path.exists(log_path):
        logger.error(f"Log file not found: {log_path}")
        return rows

    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse pipe-separated chunk_ids into a list
            raw_ids = row.get("retrieved_chunk_ids", "")
            row["retrieved_chunk_ids"] = [cid for cid in raw_ids.split("|") if cid.strip()]
            rows.append(row)

    logger.info(f"Loaded {len(rows)} queries from {log_path}")
    return rows


def load_golden(golden_path: str) -> Dict[str, List[str]]:
    """
    Loads the golden dataset (ground-truth relevance labels).

    Expected JSON format:
        [
            {
                "query": "What is the main finding?",
                "relevant_chunk_ids": ["0", "1", "5"]
            },
            ...
        ]

    Args:
        golden_path: Path to golden_dataset.json.

    Returns:
        Dict mapping query string → list of relevant chunk_id strings.
        Queries are lowercased and stripped for robust matching.
    """
    if not os.path.exists(golden_path):
        logger.error(f"Golden dataset not found: {golden_path}")
        return {}

    with open(golden_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    golden = {}
    for item in data:
        query = item.get("query", "").strip().lower()
        rel_ids = [str(cid) for cid in item.get("relevant_chunk_ids", [])]
        if query:
            golden[query] = rel_ids

    logger.info(f"Loaded {len(golden)} golden queries from {golden_path}")
    return golden


# ── Main Metrics Computation ───────────────────────────────────────────────────

def compute_metrics(log_rows: List[Dict], golden: Dict[str, List[str]], k: int) -> Dict[str, Any]:
    """
    Computes aggregate metrics over all queries in the log that have
    a matching entry in the golden dataset.

    Args:
        log_rows: List of log row dicts from load_log().
        golden:   Dict of {query → relevant_chunk_ids} from load_golden().
        k:        Cutoff rank for metric computation.

    Returns:
        Dict with all aggregate metrics and metadata fields.
    """
    precisions, recalls, mrrs, ndcgs, hits = [], [], [], [], []
    matched_rows = []

    for row in log_rows:
        query_key = row.get("query", "").strip().lower()
        if query_key not in golden:
            # Skip queries not in the golden set
            continue

        relevant     = golden[query_key]
        retrieved    = row["retrieved_chunk_ids"]
        matched_rows.append(row)

        precisions.append(precision_at_k(retrieved, relevant, k))
        recalls.append(recall_at_k(retrieved, relevant, k))
        mrrs.append(mean_reciprocal_rank(retrieved, relevant))
        ndcgs.append(ndcg_at_k(retrieved, relevant, k))
        hits.append(hit_rate_at_k(retrieved, relevant, k))

    n = len(matched_rows)
    if n == 0:
        logger.warning("No queries matched between log and golden dataset.")
        return {}

    def safe_mean(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    # Latency averages (from all logged rows, not just matched)
    all_retrieval_latencies = [float(r.get("retrieval_latency_ms", 0)) for r in log_rows]
    all_gen_latencies       = [float(r.get("generation_latency_ms", 0)) for r in log_rows]
    all_total_latencies     = [float(r.get("total_latency_ms", 0))      for r in log_rows]

    # Pull config from first row
    first = matched_rows[0]
    
    mode_name = first.get("retrieval_mode", "unknown")
    # Formatting for terminal and summary: 'hybrid_rerank' -> 'Hybrid+Rerank', 'dense' -> 'Dense'
    if mode_name == "hybrid_rerank":
        mode_display = "Hybrid+Rerank"
    else:
        mode_display = mode_name.capitalize()

    return {
        "Retrieval Mode":                  mode_display,
        "Precision@K":                     f"{safe_mean(precisions):.2f}",
        "Recall@K":                        f"{safe_mean(recalls):.2f}",
        "MRR":                             f"{safe_mean(mrrs):.2f}",
        "nDCG":                            f"{safe_mean(ndcgs):.2f}",
        "Hit Rate":                        f"{safe_mean(hits):.2f}",
        "Average Retrieval Latency (ms)":  int(safe_mean(all_retrieval_latencies)),
        "Average Generation Latency (ms)": int(safe_mean(all_gen_latencies)),
        "Average Total Latency (ms)":      int(safe_mean(all_total_latencies)),
        "TopK":                            first.get("top_k", k),
        "Chunk Size":                      first.get("chunk_size", "?"),
        "Chunk Overlap":                   first.get("chunk_overlap", "?"),
        "Number of Queries":               n,
        "_raw_mode":                       mode_name  # internal use for naming the individual csv
    }



def write_summary(results: List[Dict[str, Any]]) -> None:
    """
    Writes summary.csv and individual {mode}_metrics.csv files.
    """
    os.makedirs(EVAL_DIR, exist_ok=True)
    
    # 1. Write individual metrics file for each mode
    for row in results:
        raw_mode = row.get("_raw_mode", "unknown")
        indiv_path = os.path.join(EVAL_DIR, f"{raw_mode}_metrics.csv")
        
        # We need a copy of row without internal fields
        clean_row = {k: v for k, v in row.items() if k in SUMMARY_FIELDNAMES}
        
        with open(indiv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
            writer.writeheader()
            writer.writerow(clean_row)
        logger.info(f"✅ Created {indiv_path}")

    # 2. Write summary.csv with all modes
    with open(SUMMARY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        for row in results:
            clean_row = {k: v for k, v in row.items() if k in SUMMARY_FIELDNAMES}
            writer.writerow(clean_row)

    logger.info(f"✅ Summary written to {SUMMARY_PATH}")


def print_comparison_table(results: List[Dict[str, Any]]) -> None:
    """
    Prints a formatted comparison table to stdout exactly like the summary.csv format.
    """
    if not results:
        print("No results to display.")
        return

    # Create format string based on columns
    header = f"{'Retrieval Mode':<15} {'P@K':>6} {'R@K':>6} {'MRR':>6} {'nDCG':>6} {'Hit%':>6} {'RetLat':>8} {'GenLat':>8} {'TotLat':>8} {'TopK':>5} {'Chunk':>6} {'Ovl':>4} {'Qs':>4}"
    print("\n" + "=" * len(header))
    print("  RAG Evaluation Summary Report")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for r in results:
        print(
            f"{r.get('Retrieval Mode'):<15} "
            f"{r.get('Precision@K'):>6} "
            f"{r.get('Recall@K'):>6} "
            f"{r.get('MRR'):>6} "
            f"{r.get('nDCG'):>6} "
            f"{r.get('Hit Rate'):>6} "
            f"{str(r.get('Average Retrieval Latency (ms)')):>8} "
            f"{str(r.get('Average Generation Latency (ms)')):>8} "
            f"{str(r.get('Average Total Latency (ms)')):>8} "
            f"{str(r.get('TopK')):>5} "
            f"{str(r.get('Chunk Size')):>6} "
            f"{str(r.get('Chunk Overlap')):>4} "
            f"{str(r.get('Number of Queries')):>4}"
        )

    print("=" * len(header) + "\n")


# ── CLI Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute RAG evaluation metrics from logged query data."
    )
    parser.add_argument(
        "--golden",
        type=str,
        default="golden_dataset.json",
        help="Path to the golden dataset JSON file."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        help="Specific mode to evaluate (dense, hybrid, hybrid_rerank). "
             "If omitted, processes all *_log.csv files found in evaluation/."
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Explicit path to a *_log.csv file. Used when --mode is specified."
    )
    parser.add_argument(
        "--k",
        type=int,
        default=6,
        help="Top-K cutoff for metric computation (default: 6)."
    )
    args = parser.parse_args()

    golden = load_golden(args.golden)
    if not golden:
        print("❌ Golden dataset is empty or missing. Aborting.")
        exit(1)

    all_results = []

    if args.mode and args.log:
        # Single mode evaluation
        rows = load_log(args.log)
        metrics = compute_metrics(rows, golden, k=args.k)
        if metrics:
            all_results.append(metrics)

    else:
        # Auto-discover all *_log.csv files in evaluation/
        if not os.path.exists(EVAL_DIR):
            print(f"❌ Evaluation directory not found: {EVAL_DIR}")
            exit(1)

        log_files = [
            f for f in os.listdir(EVAL_DIR)
            if f.endswith("_log.csv")
        ]

        if not log_files:
            print(f"❌ Error: No evaluation log files found in '{EVAL_DIR}'.")
            print("Please ensure you have run the chatbot with EVALUATION_MODE=true and asked questions.")
            exit(1)

        for log_file in sorted(log_files):
            log_path = os.path.join(EVAL_DIR, log_file)
            rows = load_log(log_path)
            if not rows:
                print(f"⚠️  Skipping {log_file} (no data found).")
                continue
            metrics = compute_metrics(rows, golden, k=args.k)
            if metrics:
                all_results.append(metrics)

    if all_results:
        print_comparison_table(all_results)
        write_summary(all_results)
    else:
        print("⚠️  No metrics computed. Ensure queries in the log match queries in the golden dataset.")
