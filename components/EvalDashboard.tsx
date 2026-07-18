// ─────────────────────────────────────────────────────────────────────────────
// components/EvalDashboard.tsx
// Professional Generation Evaluation Dashboard.
//
// Renders a collapsible panel beneath every assistant message showing:
//   • Faithfulness Gauge (SVG arc)
//   • Hallucination Indicator (badge)
//   • Supported vs Unsupported Claims (horizontal bar chart)
//   • Context Utilization Ring
//   • Answer Relevancy Score
//   • Response Latency Stacked Chart
//   • Pipeline Diagram with per-stage timing
//   • Overall Score Badge
//   • Retrieved Context Viewer (expandable)
//   • Claims Detail (expandable)
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useState } from "react";
import type { EvaluationReport } from "@/types";

interface EvalDashboardProps {
  evaluation: EvaluationReport;
}

// ── Helper: percentage formatter ──────────────────────────────────────────────
const pct = (v: number) => `${Math.round(v * 100)}%`;
const ms  = (v: number) => v >= 1000 ? `${(v / 1000).toFixed(2)}s` : `${Math.round(v)}ms`;

// ── Helper: score → color class ───────────────────────────────────────────────
function scoreColor(v: number): string {
  if (v >= 0.75) return "eval-good";
  if (v >= 0.45) return "eval-warn";
  return "eval-bad";
}

// ── Helper: overall score → letter grade ─────────────────────────────────────
function grade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 55) return "C";
  return "F";
}

function gradeColor(score: number): string {
  if (score >= 80) return "eval-grade-green";
  if (score >= 60) return "eval-grade-amber";
  return "eval-grade-red";
}

// ── SVG Arc Gauge ─────────────────────────────────────────────────────────────
function ArcGauge({ value, label, size = 80 }: { value: number; label: string; size?: number }) {
  const r       = size * 0.38;
  const cx      = size / 2;
  const cy      = size / 2;
  const stroke  = size * 0.088;
  const circ    = Math.PI * r;                          // half-circle circumference
  const filled  = circ * Math.min(value, 1);
  const gap     = circ - filled;

  // Color gradient: red → amber → green
  const col = value >= 0.75 ? "#22c55e" : value >= 0.45 ? "#f59e0b" : "#ef4444";

  return (
    <div className="eval-gauge-wrap" style={{ width: size, height: size * 0.65 }}>
      <svg width={size} height={size * 0.68} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Track */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={col}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${gap}`}
          style={{ filter: `drop-shadow(0 0 4px ${col}88)` }}
        />
        {/* Center label */}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          fill={col}
          fontSize={size * 0.18}
          fontWeight="700"
          fontFamily="Inter, system-ui, sans-serif"
        >
          {Math.round(value * 100)}%
        </text>
        <text
          x={cx}
          y={cy + size * 0.13}
          textAnchor="middle"
          fill="rgba(255,255,255,0.45)"
          fontSize={size * 0.1}
          fontFamily="Inter, system-ui, sans-serif"
        >
          {label}
        </text>
      </svg>
    </div>
  );
}

// ── Circular Progress Ring ────────────────────────────────────────────────────
function Ring({ value, label, size = 64 }: { value: number; label: string; size?: number }) {
  const r     = size * 0.38;
  const circ  = 2 * Math.PI * r;
  const fill  = circ * Math.min(value, 1);
  const gap   = circ - fill;
  const col   = value >= 0.75 ? "#22c55e" : value >= 0.45 ? "#f59e0b" : "#ef4444";

  return (
    <div className="eval-ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={size*0.1} />
        <circle
          cx={size/2} cy={size/2} r={r}
          fill="none"
          stroke={col}
          strokeWidth={size*0.1}
          strokeLinecap="round"
          strokeDasharray={`${fill} ${gap}`}
          strokeDashoffset={circ * 0.25}   /* rotate to start from top */
          style={{ filter: `drop-shadow(0 0 3px ${col}88)` }}
        />
        <text x={size/2} y={size/2 + 5} textAnchor="middle"
          fill={col} fontSize={size*0.2} fontWeight="700"
          fontFamily="Inter, system-ui, sans-serif">
          {Math.round(value * 100)}%
        </text>
      </svg>
      <span className="eval-ring-label">{label}</span>
    </div>
  );
}

// ── Latency Bar Segment ───────────────────────────────────────────────────────
function LatencyBar({ eval: ev }: { eval: EvaluationReport }) {
  const total = ev.total_latency_ms || 1;
  const segments = [
    { label: "Retrieval",   ms: ev.retrieval_latency_ms,  color: "#7c3aed" },
    { label: "Reranking",   ms: ev.reranking_latency_ms,  color: "#0d9488" },
    { label: "Generation",  ms: ev.generation_latency_ms, color: "#2563eb" },
  ];
  const overhead = Math.max(0, total - segments.reduce((a, s) => a + s.ms, 0));
  if (overhead > 1) segments.push({ label: "Overhead", ms: overhead, color: "#4b5563" });

  return (
    <div className="eval-latency-section">
      {/* Stacked bar */}
      <div className="eval-latency-bar">
        {segments.map((seg) => (
          <div
            key={seg.label}
            className="eval-latency-segment"
            style={{ width: `${(seg.ms / total) * 100}%`, background: seg.color }}
            title={`${seg.label}: ${ms(seg.ms)}`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="eval-latency-legend">
        {segments.map((seg) => (
          <div key={seg.label} className="eval-latency-legend-item">
            <span className="eval-latency-dot" style={{ background: seg.color }} />
            <span className="eval-latency-legend-label">{seg.label}</span>
            <span className="eval-latency-legend-val">{ms(seg.ms)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Pipeline Diagram ──────────────────────────────────────────────────────────
function PipelineDiagram({ ev }: { ev: EvaluationReport }) {
  const stages = [
    { icon: "🔍", label: "Retrieval",   time: ev.retrieval_latency_ms,   color: "#7c3aed" },
    { icon: "⚖️",  label: "Re-ranking", time: ev.reranking_latency_ms,   color: "#0d9488" },
    { icon: "🤖", label: "Generation",  time: ev.generation_latency_ms,  color: "#2563eb" },
    { icon: "✅", label: "Evaluation",  time: 0,                          color: "#22c55e" },
  ];
  return (
    <div className="eval-pipeline">
      {stages.map((s, i) => (
        <div key={s.label} className="eval-pipeline-row">
          <div className="eval-pipeline-stage" style={{ borderColor: s.color + "55" }}>
            <span className="eval-pipeline-icon">{s.icon}</span>
            <span className="eval-pipeline-label">{s.label}</span>
            {s.time > 0 && (
              <span className="eval-pipeline-time" style={{ color: s.color }}>{ms(s.time)}</span>
            )}
          </div>
          {i < stages.length - 1 && <div className="eval-pipeline-arrow">▼</div>}
        </div>
      ))}
    </div>
  );
}

// ── Main Dashboard Component ──────────────────────────────────────────────────
export default function EvalDashboard({ evaluation: ev }: EvalDashboardProps) {
  const [open,        setOpen]        = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [showClaims,  setShowClaims]  = useState(false);

  const totalClaims = ev.supported_claims + ev.unsupported_claims;

  return (
    <div className="eval-root">
      {/* ── Toggle Button ─────────────────────────────────────────────────── */}
      <button
        id="eval-toggle-btn"
        className={`eval-toggle ${open ? "eval-toggle--open" : ""}`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="Toggle evaluation dashboard"
      >
        <span className="eval-toggle-icon">📊</span>
        <span className="eval-toggle-text">Evaluation Report</span>
        {/* Quick summary badges always visible */}
        <span className={`eval-quick-badge ${ev.hallucination_detected ? "eval-badge-red" : "eval-badge-green"}`}>
          {ev.hallucination_detected ? "⚠️ Hallucination" : "✅ Grounded"}
        </span>
        <span className={`eval-quick-badge eval-badge-score ${gradeColor(ev.overall_score)}`}>
          {ev.overall_score}/100
        </span>
        <span className="eval-toggle-chevron">{open ? "▲" : "▼"}</span>
      </button>

      {/* ── Expanded Dashboard ─────────────────────────────────────────────── */}
      {open && (
        <div className="eval-dashboard">

          {/* ── Row 1: Gauges + Overall Score ──────────────────────────────── */}
          <div className="eval-row eval-row-top">

            {/* Faithfulness Gauge */}
            <div className="eval-card eval-card-gauge">
              <div className="eval-card-title">Faithfulness</div>
              <ArcGauge value={ev.faithfulness_score} label="score" size={96} />
            </div>

            {/* Hallucination Indicator */}
            <div className="eval-card eval-card-halu">
              <div className="eval-card-title">Hallucination</div>
              <div className={`eval-halu-badge ${ev.hallucination_detected ? "eval-halu-yes" : "eval-halu-no"}`}>
                {ev.hallucination_detected ? (
                  <><span className="eval-halu-icon">⚠️</span> Detected</>
                ) : (
                  <><span className="eval-halu-icon">✅</span> None</>
                )}
              </div>
              <div className="eval-halu-sub">
                {ev.hallucination_detected
                  ? "Answer contains unsupported claims"
                  : "All claims grounded in context"}
              </div>
            </div>

            {/* Context Utilization Ring */}
            <div className="eval-card eval-card-ring">
              <div className="eval-card-title">Context Utilization</div>
              <Ring value={ev.context_utilization} label="used" size={72} />
            </div>

            {/* Answer Relevancy Ring */}
            <div className="eval-card eval-card-ring">
              <div className="eval-card-title">Answer Relevancy</div>
              <Ring value={ev.answer_relevancy} label="match" size={72} />
            </div>

            {/* Overall Score */}
            <div className="eval-card eval-card-score">
              <div className="eval-card-title">Overall Score</div>
              <div className={`eval-overall-score ${gradeColor(ev.overall_score)}`}>
                {ev.overall_score}
                <span className="eval-overall-denom">/100</span>
              </div>
              <div className={`eval-grade-pill ${gradeColor(ev.overall_score)}`}>{grade(ev.overall_score)}</div>
            </div>
          </div>

          {/* ── Row 2: Claims Bar + Latency ─────────────────────────────────── */}
          <div className="eval-row eval-row-mid">

            {/* Claims Chart */}
            <div className="eval-card eval-card-claims">
              <div className="eval-card-title">Claims Analysis</div>
              <div className="eval-claims-counts">
                <div className="eval-claim-stat eval-claim-stat--green">
                  <span className="eval-claim-num">{ev.supported_claims}</span>
                  <span className="eval-claim-label">Supported</span>
                </div>
                <div className="eval-claim-divider" />
                <div className="eval-claim-stat eval-claim-stat--red">
                  <span className="eval-claim-num">{ev.unsupported_claims}</span>
                  <span className="eval-claim-label">Unsupported</span>
                </div>
              </div>
              {/* Horizontal segmented bar */}
              {totalClaims > 0 && (
                <div className="eval-claims-bar-wrap">
                  <div className="eval-claims-bar">
                    <div
                      className="eval-claims-seg eval-claims-seg--green"
                      style={{ width: `${(ev.supported_claims / totalClaims) * 100}%` }}
                    />
                    <div
                      className="eval-claims-seg eval-claims-seg--red"
                      style={{ width: `${(ev.unsupported_claims / totalClaims) * 100}%` }}
                    />
                  </div>
                  <div className="eval-claims-bar-labels">
                    <span>{Math.round((ev.supported_claims / totalClaims) * 100)}% supported</span>
                    <span>{totalClaims} total</span>
                  </div>
                </div>
              )}
            </div>

            {/* Latency Chart */}
            <div className="eval-card eval-card-latency">
              <div className="eval-card-title">Response Latency</div>
              <LatencyBar eval={ev} />
              <div className="eval-latency-total">
                Total: <strong>{ms(ev.total_latency_ms)}</strong>
              </div>
            </div>
          </div>

          {/* ── Row 3: Pipeline Diagram ──────────────────────────────────────── */}
          <div className="eval-row">
            <div className="eval-card eval-card-pipeline">
              <div className="eval-card-title">Retrieval Pipeline</div>
              <PipelineDiagram ev={ev} />
            </div>

            {/* Metrics Summary Table */}
            <div className="eval-card eval-card-summary">
              <div className="eval-card-title">Evaluation Summary</div>
              <table className="eval-summary-table">
                <tbody>
                  <tr>
                    <td className="eval-tbl-key">Faithfulness</td>
                    <td className={`eval-tbl-val ${scoreColor(ev.faithfulness_score)}`}>
                      {pct(ev.faithfulness_score)}
                    </td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Hallucination</td>
                    <td className={`eval-tbl-val ${ev.hallucination_detected ? "eval-bad" : "eval-good"}`}>
                      {ev.hallucination_detected ? "Yes ⚠️" : "No ✅"}
                    </td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Supported Claims</td>
                    <td className="eval-tbl-val eval-good">{ev.supported_claims}</td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Unsupported Claims</td>
                    <td className={`eval-tbl-val ${ev.unsupported_claims > 0 ? "eval-bad" : "eval-good"}`}>
                      {ev.unsupported_claims}
                    </td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Context Utilization</td>
                    <td className={`eval-tbl-val ${scoreColor(ev.context_utilization)}`}>
                      {pct(ev.context_utilization)}
                    </td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Answer Relevancy</td>
                    <td className={`eval-tbl-val ${scoreColor(ev.answer_relevancy)}`}>
                      {pct(ev.answer_relevancy)}
                    </td>
                  </tr>
                  {ev.semantic_score !== undefined && (
                    <tr>
                      <td className="eval-tbl-key">Semantic Score</td>
                      <td className={`eval-tbl-val ${scoreColor(ev.semantic_score)}`}>
                        {pct(ev.semantic_score)}
                      </td>
                    </tr>
                  )}
                  {ev.tfidf_score !== undefined && (
                    <tr>
                      <td className="eval-tbl-key">TF-IDF Score</td>
                      <td className={`eval-tbl-val ${scoreColor(ev.tfidf_score)}`}>
                        {pct(ev.tfidf_score)}
                      </td>
                    </tr>
                  )}
                  {ev.keyword_score !== undefined && (
                    <tr>
                      <td className="eval-tbl-key">Keyword Score</td>
                      <td className={`eval-tbl-val ${scoreColor(ev.keyword_score)}`}>
                        {pct(ev.keyword_score)}
                      </td>
                    </tr>
                  )}
                  <tr><td colSpan={2} className="eval-tbl-divider" /></tr>
                  <tr>
                    <td className="eval-tbl-key">Retrieval Latency</td>
                    <td className="eval-tbl-val">{ms(ev.retrieval_latency_ms)}</td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Re-ranking Latency</td>
                    <td className="eval-tbl-val">{ms(ev.reranking_latency_ms)}</td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Generation Time</td>
                    <td className="eval-tbl-val">{ms(ev.generation_latency_ms)}</td>
                  </tr>
                  <tr>
                    <td className="eval-tbl-key">Total Time</td>
                    <td className="eval-tbl-val"><strong>{ms(ev.total_latency_ms)}</strong></td>
                  </tr>
                  <tr><td colSpan={2} className="eval-tbl-divider" /></tr>
                  <tr>
                    <td className="eval-tbl-key">Overall Score</td>
                    <td className={`eval-tbl-val eval-tbl-score ${gradeColor(ev.overall_score)}`}>
                      {ev.overall_score}/100 ({grade(ev.overall_score)})
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Row 4: Context Viewer (expandable) ──────────────────────────── */}
          {ev.retrieved_chunks.length > 0 && (
            <div className="eval-row">
              <div className="eval-card eval-card-full">
                <button
                  className="eval-expander-btn"
                  onClick={() => setShowContext(!showContext)}
                  aria-expanded={showContext}
                >
                  <span>📄 Retrieved Context ({ev.retrieved_chunks.length} chunks)</span>
                  <span>{showContext ? "▲" : "▼"}</span>
                </button>
                {showContext && (
                  <div className="eval-context-list">
                    {ev.retrieved_chunks.map((chunk, i) => (
                      <div key={i} className="eval-context-chunk">
                        <div className="eval-chunk-header">
                          <span className="eval-chunk-num">Chunk {i + 1}</span>
                        </div>
                        <p className="eval-chunk-text">{chunk}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Row 5: Claims Detail (expandable) ───────────────────────────── */}
          {ev.claims.length > 0 && (
            <div className="eval-row">
              <div className="eval-card eval-card-full">
                <button
                  className="eval-expander-btn"
                  onClick={() => setShowClaims(!showClaims)}
                  aria-expanded={showClaims}
                >
                  <span>🔬 Claims Analysis ({ev.claims.length} claims extracted)</span>
                  <span>{showClaims ? "▲" : "▼"}</span>
                </button>
                {showClaims && (
                  <div className="eval-claims-detail">
                    {ev.supported_claim_list.map((claim, i) => (
                      <div key={`s-${i}`} className="eval-claim-item eval-claim-item--supported">
                        <span className="eval-claim-status">✅</span>
                        <span className="eval-claim-text">{claim}</span>
                      </div>
                    ))}
                    {ev.unsupported_claim_list.map((claim, i) => (
                      <div key={`u-${i}`} className="eval-claim-item eval-claim-item--unsupported">
                        <span className="eval-claim-status">⚠️</span>
                        <span className="eval-claim-text">{claim}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
