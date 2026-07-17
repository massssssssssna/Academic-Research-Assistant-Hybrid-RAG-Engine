// ─────────────────────────────────────────────────────────────────────────────
// types/index.ts
// Central TypeScript interfaces for the Academic RAG Assistant.
// These are the shapes passed between every component and hook.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A single chat message in a session.
 *
 * - role       "user" | "assistant"
 * - content    The text body (supports basic **bold** markdown)
 * - source     Optional array of Qdrant chunk citations.
 *              They will be parsed by the frontend to display
 *              the "Grounded Sources (Qdrant Chunks)" expander.
 * - timestamp  JavaScript Date of when the message was created
 */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: string[];         // Qdrant chunk citations, e.g. "Page 3: Paragraph 2 — ..."
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
