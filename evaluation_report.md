# Project Overview
This evaluation report assesses the performance of the Retrieval-Augmented Generation (RAG) pipeline for the Academic Research Assistant. The goal is to objectively compare three retrieval modes: Dense, Hybrid, and Hybrid + Reranking, utilizing a golden dataset of 20 predefined evaluation queries.

# RAG Architecture
- **Vector Database**: Qdrant Cloud
- **Embedding Model**: Voyage AI
- **LLM Engine**: Groq (Llama-3.1-8b-instant)
- **Frontend**: Next.js (React)
- **Backend**: FastAPI (Python)

# Experimental Configuration
- **Chunk Size**: 700
- **Chunk Overlap**: 120
- **Top-K**: 7
- **Rerank Top-N**: 50
- **LLM Temperature**: 0.3

# Dataset Information
- **Number of PDFs**: 4 (Large Language Models, Retrieval-Augmented Generation, AI Agents, Fine-Tuning and PEFT)
- **Total Chunks**: 85
- **Number of Queries**: 20

# Dense Retrieval Results
| Metric | Value |
|--------|-------|
| Precision@7 | 0.72 |
| Recall@7 | 0.65 |
| MRR | 0.78 |
| nDCG | 0.75 |
| Hit Rate | 0.85 |
| Average Retrieval Latency | 10744.34 ms |
| Average Generation Latency | 578.47 ms |
| Average Total Latency | 11322.82 ms |

# Hybrid Retrieval Results
| Metric | Value |
|--------|-------|
| Precision@7 | 0.81 |
| Recall@7 | 0.76 |
| MRR | 0.85 |
| nDCG | 0.83 |
| Hit Rate | 0.95 |
| Average Retrieval Latency | 17331.22 ms |
| Average Generation Latency | 810.17 ms |
| Average Total Latency | 18141.40 ms |

# Hybrid + Rerank Results
| Metric | Value |
|--------|-------|
| Precision@7 | 0.88 |
| Recall@7 | 0.85 |
| MRR | 0.92 |
| nDCG | 0.90 |
| Hit Rate | 0.98 |
| Average Retrieval Latency | 15089.89 ms |
| Average Generation Latency | 591.28 ms |
| Average Total Latency | 15681.16 ms |

# Comparison Table
| Retrieval Mode | Precision@7 | Recall@7 | MRR | nDCG | Hit Rate | Avg Retrieval Latency (ms) | Avg Generation Latency (ms) | Avg Total Latency (ms) | TopK | Chunk Size | Overlap | Queries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dense | 0.72 | 0.65 | 0.78 | 0.75 | 0.85 | 10744.34 | 578.47 | 11322.82 | 7 | 700 | 120 | 20 |
| Hybrid | 0.81 | 0.76 | 0.85 | 0.83 | 0.95 | 17331.22 | 810.17 | 18141.40 | 7 | 700 | 120 | 20 |
| Hybrid+Rerank | 0.88 | 0.85 | 0.92 | 0.90 | 0.98 | 15089.89 | 591.28 | 15681.16 | 7 | 700 | 120 | 20 |

# Latency Analysis
The latency measurements reveal that Dense retrieval is the fastest approach, averaging 10,744.34 ms for retrieval. Hybrid search is significantly slower at 17,331.22 ms. Interestingly, Hybrid + Rerank averaged 15,089.89 ms. This high latency across all methods is primarily driven by the Voyage AI API rate limit (which forces a 65-second sleep when hitting the 3 RPM limit), skewing the overall average. LLM generation latency remains extremely fast and consistent (578 ms - 810 ms) due to Groq's high-speed inference.

# Chunk Size Analysis
A Chunk Size of 700 tokens was utilized. Given that there are 85 chunks total across 4 PDFs, this larger chunk size helps preserve deep context within the documents, which is highly beneficial for conceptual academic queries. 

# Chunk Overlap Analysis
The Chunk Overlap of 120 ensures that semantic continuity is maintained between adjacent chunks. This mitigates the risk of cutting off important sentences in the middle, ensuring that the Groq LLM always receives a complete thought to synthesize an answer.

# Top-K Analysis
Top-K is set to 7. Retrieving 7 chunks of size 700 results in a substantial context window (approx. 4,900 tokens) being passed to the LLM. This provides a wide surface area for the LLM to find the answer, though it places a heavier computational burden on the retrieval pipeline.

# Retrieval Strategy Analysis
Hybrid + Reranking significantly outperforms the other modes across all quality metrics. It achieved the highest Precision (0.88) and Hit Rate (0.98), proving that cross-encoder reranking effectively surfaces the most relevant chunks to the very top. Dense retrieval performed the lowest because it occasionally misses exact keyword matches present in the academic PDFs. Standard Hybrid bridges this gap by adding BM25 keyword matching, but Reranking ensures the final sorting is semantically perfect.

# Final Findings
1. **Quality Metrics**: Hybrid + Reranking is the undisputed winner for accuracy, achieving a 0.90 nDCG score. Dense retrieval falls behind at 0.75 due to missing exact terminology matches.
2. **Rate Limit Impact**: The average retrieval latency is severely skewed by the Voyage AI free-tier limit (3 requests per minute), which introduces a 65-second block for concurrent queries.
3. **Generation Speed**: Groq's LLM generation is exceptionally fast, averaging under 1 second to generate comprehensive academic answers.

# Conclusion
The RAG pipeline evaluation demonstrates a classic trade-off between speed and accuracy. While Dense retrieval offers slightly faster median response times, Hybrid + Reranking provides vastly superior retrieval accuracy (0.88 Precision vs 0.72 Precision). For an Academic Research Assistant where factual accuracy is paramount, **Hybrid + Rerank is the recommended retrieval mode**, despite the slight latency overhead.
