// ─────────────────────────────────────────────────────────────────────────────
// app/page.tsx
// Root page — knowledge base is pre-indexed in Qdrant.
// No PDF upload. Pure Q&A + automatic Generation Evaluation.
//
// Flow per message:
//   User types question
//     → POST /api/chat
//     → Backend: Hybrid Retrieval → Reranking → LLM → Evaluation
//     → Response: { answer, evaluation }
//     → EvalDashboard renders below assistant bubble automatically
// ─────────────────────────────────────────────────────────────────────────────

"use client";

import { useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import ChatArea from "@/components/ChatArea";
import TestingPanel from "@/components/TestingPanel";
import { useChatSessions } from "@/hooks/useChatSessions";

const TOP_K = 7;

export default function HomePage() {
  const {
    sessions,
    activeSessionId,
    activeSession,
    setActiveSessionId,
    createSession,
    deleteSession,
    addMessage,
    clearMessages,
  } = useChatSessions();

  const [inputValue,    setInputValue]    = useState<string>("");
  const [isLoading,     setIsLoading]     = useState<boolean>(false);
  const [testPanelOpen, setTestPanelOpen] = useState<boolean>(false);

  // ── Core send handler ─────────────────────────────────────────────────
  const sendQuery = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    const sessionId = activeSessionId ?? createSession("New Research Chat");
    addMessage(sessionId, { role: "user", content: query });
    setInputValue("");
    setIsLoading(true);

    const chatHistory = activeSession?.messages.map((m) => ({
      role:    m.role,
      content: m.content,
    })) ?? [];

    try {
      const res = await fetch("/api/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ query, top_k: TOP_K, chat_history: chatHistory }),
      });

      if (!res.ok) {
        let errText = await res.text();
        try {
          const errJson = JSON.parse(errText);
          errText = errJson?.detail || errText;
        } catch(e) {}
        addMessage(sessionId, {
          role:    "assistant",
          content: `❌ **Query failed (${res.status}):** \n\n\`\`\`text\n${errText}\n\`\`\``,
        });
        return;
      }

      const data = await res.json();

      // Attach evaluation report — EvalDashboard renders it automatically
      addMessage(sessionId, {
        role:       "assistant",
        content:    data.answer,
        source:     data.sources,
        evaluation: data.evaluation ?? undefined,
      });

    } catch (err: any) {
      addMessage(sessionId, {
        role:    "assistant",
        content: `⚠️ **Connection error:** ${err.message}. Make sure the backend is running on port 8000.`,
      });
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionId, activeSession, createSession, addMessage, isLoading]);

  const handleSend = useCallback(() => sendQuery(inputValue.trim()), [inputValue, sendQuery]);

  const handleNewSession = useCallback(() => {
    createSession("New Research Chat");
    setInputValue("");
  }, [createSession]);

  const handleClearChat = useCallback(() => {
    if (activeSessionId) clearMessages(activeSessionId);
  }, [activeSessionId, clearMessages]);

  return (
    <div className="app-root">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNew={handleNewSession}
        onDelete={deleteSession}
        onOpenTestPanel={() => setTestPanelOpen(true)}
      />

      <div className="workspace">
        <Header
          session={activeSession}
          onClearChat={handleClearChat}
        />

        <ChatArea
          session={activeSession}
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSend={handleSend}
          isLoading={isLoading}
          topK={TOP_K}
        />
      </div>

      {testPanelOpen && (
        <TestingPanel
          onClose={() => setTestPanelOpen(false)}
          onSendQuery={(q) => { sendQuery(q); setTestPanelOpen(false); }}
        />
      )}
    </div>
  );
}
