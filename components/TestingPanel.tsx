// ─────────────────────────────────────────────────────────────────────────────
// components/TestingPanel.tsx
// Slide-out Evaluation Testing Panel.
//
// A full-screen overlay panel with:
//   • 10 standard RAG/AI research questions
//   • 3 adversarial hallucination-trap questions
// Each question can be sent to the chat with one click.
// Includes a live preview of which category the question belongs to.
// ─────────────────────────────────────────────────────────────────────────────

"use client";

interface TestingPanelProps {
  onClose:     () => void;
  onSendQuery: (query: string) => void;
}

// ── Test Question Definitions ─────────────────────────────────────────────────
const RAG_QUESTIONS = [
  {
    id:       "q1",
    category: "RAG Fundamentals",
    icon:     "📚",
    question: "What is Retrieval-Augmented Generation?",
    expected: "grounded",
    hint:     "Should be found in any RAG paper.",
  },
  {
    id:       "q2",
    category: "RAG Fundamentals",
    icon:     "✂️",
    question: "Explain Chunking in RAG.",
    expected: "grounded",
    hint:     "Covered in most RAG architecture papers.",
  },
  {
    id:       "q3",
    category: "Retrieval",
    icon:     "🔀",
    question: "What is Hybrid Search?",
    expected: "grounded",
    hint:     "Combines dense and sparse retrieval.",
  },
  {
    id:       "q4",
    category: "Retrieval",
    icon:     "🧠",
    question: "Explain Dense Retrieval.",
    expected: "grounded",
    hint:     "Embedding-based semantic search.",
  },
  {
    id:       "q5",
    category: "Retrieval",
    icon:     "📊",
    question: "What is BM25?",
    expected: "grounded",
    hint:     "Probabilistic term-frequency model.",
  },
  {
    id:       "q6",
    category: "Retrieval",
    icon:     "🏆",
    question: "What is Re-ranking?",
    expected: "grounded",
    hint:     "CrossEncoder-based precision pass.",
  },
  {
    id:       "q7",
    category: "Comparison",
    icon:     "⚖️",
    question: "What is the difference between Dense and Sparse Retrieval?",
    expected: "grounded",
    hint:     "Tests comparative understanding.",
  },
  {
    id:       "q8",
    category: "Embeddings",
    icon:     "📐",
    question: "What are Embeddings?",
    expected: "grounded",
    hint:     "Vector representations of text.",
  },
  {
    id:       "q9",
    category: "Architecture",
    icon:     "🔧",
    question: "Explain the Transformer Architecture.",
    expected: "grounded",
    hint:     "Attention mechanism, encoder-decoder.",
  },
  {
    id:       "q10",
    category: "Prompting",
    icon:     "✍️",
    question: "What is Prompt Engineering?",
    expected: "grounded",
    hint:     "Crafting effective LLM prompts.",
  },
];

const ADVERSARIAL_QUESTIONS = [
  {
    id:       "a1",
    category: "Hallucination Trap",
    icon:     "🚨",
    question: "Who invented ChatGPT in 1980?",
    expected: "hallucination",
    hint:     "ChatGPT was released in 2022 — hallucination expected.",
  },
  {
    id:       "a2",
    category: "Hallucination Trap",
    icon:     "🚨",
    question: "What is the exact number of transformer layers used in the BM25 algorithm?",
    expected: "hallucination",
    hint:     "BM25 has no transformer layers — category confusion trap.",
  },
  {
    id:       "a3",
    category: "Hallucination Trap",
    icon:     "🚨",
    question: "Explain the quantum entanglement mechanism used in Qdrant's vector search.",
    expected: "hallucination",
    hint:     "Qdrant does not use quantum mechanics — fabrication trap.",
  },
];

export default function TestingPanel({ onClose, onSendQuery }: TestingPanelProps) {
  return (
    <div className="test-panel-overlay" role="dialog" aria-modal="true" aria-label="Evaluation Test Suite">
      {/* ── Backdrop ──────────────────────────────────────────────────────── */}
      <div className="test-panel-backdrop" onClick={onClose} />

      {/* ── Panel ─────────────────────────────────────────────────────────── */}
      <div className="test-panel">
        {/* Header */}
        <div className="test-panel-header">
          <div className="test-panel-title-row">
            <span className="test-panel-emoji">🧪</span>
            <div>
              <h2 className="test-panel-title">Evaluation Test Suite</h2>
              <p className="test-panel-subtitle">
                Click any question to send it to the chat. Watch the evaluation dashboard populate automatically.
              </p>
            </div>
          </div>
          <button
            id="close-test-panel-btn"
            className="test-panel-close"
            onClick={onClose}
            aria-label="Close test panel"
          >
            ✕
          </button>
        </div>

        {/* ── Legend ────────────────────────────────────────────────────────── */}
        <div className="test-panel-legend">
          <div className="test-legend-item">
            <span className="test-legend-dot test-legend-green" />
            Expected: Grounded (faithfulness ↑)
          </div>
          <div className="test-legend-item">
            <span className="test-legend-dot test-legend-red" />
            Expected: Hallucination detected
          </div>
        </div>

        {/* ── Scrollable Content ─────────────────────────────────────────────── */}
        <div className="test-panel-body">

          {/* Standard RAG Questions */}
          <div className="test-section-heading">
            📚 RAG Research Questions
            <span className="test-section-count">{RAG_QUESTIONS.length} questions</span>
          </div>
          <div className="test-questions-grid">
            {RAG_QUESTIONS.map((q) => (
              <button
                key={q.id}
                id={`test-btn-${q.id}`}
                className="test-question-card test-question-card--grounded"
                onClick={() => { onSendQuery(q.question); onClose(); }}
                aria-label={`Test: ${q.question}`}
              >
                <div className="test-q-top">
                  <span className="test-q-icon">{q.icon}</span>
                  <span className="test-q-category">{q.category}</span>
                  <span className="test-q-badge test-q-badge--green">✅ Grounded</span>
                </div>
                <p className="test-q-text">{q.question}</p>
                <p className="test-q-hint">{q.hint}</p>
              </button>
            ))}
          </div>

          {/* Adversarial Hallucination Questions */}
          <div className="test-section-heading test-section-heading--red">
            🚨 Adversarial Hallucination Tests
            <span className="test-section-count">{ADVERSARIAL_QUESTIONS.length} traps</span>
          </div>
          <p className="test-adversarial-desc">
            These questions contain false premises or ask about topics that cannot be in the uploaded PDF.
            The evaluation system should correctly detect hallucinations (faithfulness &lt; 50%, hallucination = Yes).
          </p>
          <div className="test-questions-grid">
            {ADVERSARIAL_QUESTIONS.map((q) => (
              <button
                key={q.id}
                id={`test-btn-${q.id}`}
                className="test-question-card test-question-card--hallucination"
                onClick={() => { onSendQuery(q.question); onClose(); }}
                aria-label={`Hallucination trap: ${q.question}`}
              >
                <div className="test-q-top">
                  <span className="test-q-icon">{q.icon}</span>
                  <span className="test-q-category">{q.category}</span>
                  <span className="test-q-badge test-q-badge--red">⚠️ Trap</span>
                </div>
                <p className="test-q-text">{q.question}</p>
                <p className="test-q-hint">{q.hint}</p>
              </button>
            ))}
          </div>

          {/* Info Footer */}
          <div className="test-panel-info">
            <div className="test-info-icon">💡</div>
            <div>
              <strong>How to use:</strong> Upload an AI/RAG research PDF first, then run these tests.
              Each answer will show an Evaluation Report with faithfulness score, hallucination detection,
              supported claims, context utilization, and response latency. Adversarial questions should
              trigger the hallucination detector regardless of what PDF is uploaded.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
