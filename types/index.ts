// ─────────────────────────────────────────────────────────────────────────────
// types/index.ts
// Central TypeScript interfaces for the Academic RAG Assistant.
// These are the shapes passed between every component and hook.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generation Evaluation Report returned by the backend after every LLM response.
 * Maps exactly to the dict returned by generation_evaluator.evaluate_response().
 */
export interface EvaluationReport {
  // ── Core Quality Metrics ──────────────────────────────────────────────────
  /** Fraction of claims in the answer supported by retrieved context [0-1] */
  faithfulness_score: number;
  /** True if faithfulness < 50% or no claims are supported */
  hallucination_detected: boolean;
  /** Number of claims grounded in retrieved chunks */
  supported_claims: number;
  /** Number of claims NOT grounded in retrieved chunks */
  unsupported_claims: number;
  /** Fraction of retrieved chunks actually used to support claims [0-1] */
  context_utilization: number;
  /** TF-IDF cosine similarity between query and answer [0-1] */
  answer_relevancy: number;
  /** Weighted composite score 0-100 */
  overall_score: number;
  /** Semantic similarity average */
  semantic_score?: number;
  /** TF-IDF similarity average */
  tfidf_score?: number;
  /** Keyword overlap average */
  keyword_score?: number;


  // ── Latency Breakdown (milliseconds) ─────────────────────────────────────
  retrieval_latency_ms: number;
  reranking_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;

  // ── Detailed Data for Dashboard Display ──────────────────────────────────
  /** All atomic claims extracted from the answer */
  claims: string[];
  /** Subset of claims that are supported by context */
  supported_claim_list: string[];
  /** Subset of claims that are NOT supported by context */
  unsupported_claim_list: string[];
  /** Raw text of retrieved chunks (for context viewer) */
  retrieved_chunks: string[];
}

/**
 * A single chat message in a session.
 *
 * - role       "user" | "assistant"
 * - content    The text body (supports basic **bold** markdown)
 * - source     Optional array of Qdrant chunk citations.
 *              They will be parsed by the frontend to display
 *              the "Grounded Sources (Qdrant Chunks)" expander.
 * - evaluation Optional generation evaluation report (assistant messages only)
 * - timestamp  JavaScript Date of when the message was created
 */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: string[];           // Qdrant chunk citations
  evaluation?: EvaluationReport; // NEW: generation evaluation report
  timestamp: Date;
}

/**
 * A full chat session — one session = one indexed PDF document.
 *
 * - id        Unique identifier (generated client-side via generateId())
 * - title     Displayed in the sidebar; defaults to the PDF filename
 * - messages  Ordered array of Message objects
 * - pdfName   Filename of the uploaded PDF (undefined until a file is uploaded)
 * - createdAt When the session was created
 * - updatedAt Last time a message was added / PDF was changed
 */
export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  pdfName?: string;
  createdAt: Date;
  updatedAt: Date;
}
