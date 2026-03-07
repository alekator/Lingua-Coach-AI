import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import { ErrorState } from "../components/feedback";
import { getErrorMessage } from "../lib/errors";
import type { ChatMessageResponse } from "../api/types";
import { useAppStore } from "../store/app-store";
import { useToastStore } from "../store/toast-store";

type ChatEntry = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
  reply?: ChatMessageResponse;
};

function engineLabel(engine: ChatMessageResponse["engine_used"]): string {
  if (engine === "openai") return "OpenAI";
  if (engine === "local") return "Local";
  if (engine === "fallback") return "Fallback";
  return "AI";
}

export function ChatPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [text, setText] = useState("I goed to school today");
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const pushToast = useToastStore((s) => s.push);
  const latestReply = useMemo(
    () =>
      [...messages]
        .reverse()
        .find((entry) => entry.role === "assistant" && entry.reply)?.reply ?? null,
    [messages],
  );
  const correctionCount = latestReply?.corrections.length ?? 0;

  async function ensureSession(): Promise<number | null> {
    if (sessionId) return sessionId;
    try {
      const response = await api.chatStart({ user_id: userId, mode: "chat" });
      setSessionId(response.session_id);
      setMessages([]);
      setStatus(`Coach session ${response.session_id} started`);
      setError("");
      pushToast("success", "Chat session started");
      return response.session_id;
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
      return null;
    }
  }

  async function onStart() {
    await ensureSession();
  }

  async function onSend(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || sending) return;
    try {
      setSending(true);
      const activeSessionId = await ensureSession();
      if (!activeSessionId) return;
      const userText = text.trim();
      const userEntry: ChatEntry = {
        id: `user-${Date.now()}`,
        role: "user",
        text: userText,
        createdAt: Date.now(),
      };
      setMessages((prev) => [...prev, userEntry]);
      const response = await api.chatMessage({ session_id: activeSessionId, text: userText });
      const assistantEntry: ChatEntry = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        text: response.assistant_text,
        createdAt: Date.now(),
        reply: response,
      };
      setMessages((prev) => [...prev, assistantEntry]);
      setText("");
      setError("");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    } finally {
      setSending(false);
    }
  }

  async function onEnd() {
    if (!sessionId) return;
    try {
      const response = await api.chatEnd({ session_id: sessionId });
      setStatus(`Coach session ${response.session_id} ${response.status}`);
      setSessionId(null);
      setError("");
      pushToast("info", "Chat session ended");
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      pushToast("error", msg);
    }
  }

  return (
    <section className="chat-page stack">
      <article className="panel chat-hero">
        <div>
          <h2>Coach Chat Studio</h2>
          <p>Run a short AI dialogue, get targeted corrections, and iterate quickly.</p>
        </div>
        <div className="chat-hero-actions">
          <button type="button" className="cta-secondary" onClick={onStart} disabled={!!sessionId}>
            Start session
          </button>
          <button type="button" className="cta-secondary" onClick={onEnd} disabled={!sessionId}>
            End session
          </button>
        </div>
      </article>

      <section className="chat-grid">
        <article className="panel chat-main-card stack">
          {status && <p className="chat-session-status">{status}</p>}
          {error && <ErrorState text={error} />}

          <section className="chat-thread" aria-label="Chat thread">
            {messages.length === 0 ? (
              <p className="chat-empty">Start a session and send your first message.</p>
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className={`chat-bubble ${message.role === "assistant" ? "assistant" : "user"}`}
                >
                  <div className="chat-bubble-head">
                    <strong>{message.role === "assistant" ? "Coach" : "You"}</strong>
                    {message.role === "assistant" && message.reply?.engine_used && (
                      <span className={`badge chat-engine-badge ${message.reply.engine_used}`}>
                        {engineLabel(message.reply.engine_used)}
                      </span>
                    )}
                  </div>
                  <p>{message.text}</p>
                </article>
              ))
            )}
          </section>

          <form onSubmit={onSend} className="chat-composer">
            <label>
              Your message
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Type one clear sentence for the coach."
              />
            </label>
            <button type="submit" className="cta-primary" disabled={!sessionId || sending || !text.trim()}>
              {sending ? "Sending..." : "Send to coach"}
            </button>
          </form>
        </article>

        <aside className="panel chat-insights-card stack">
          <h3>Live insights</h3>
          <div className="chat-kpi-grid">
            <article>
              <p>Messages</p>
              <strong>{messages.length}</strong>
            </article>
            <article>
              <p>Corrections</p>
              <strong>{correctionCount}</strong>
            </article>
            <article>
              <p>Session</p>
              <strong>{sessionId ? "active" : "idle"}</strong>
            </article>
            <article>
              <p>Runtime</p>
              <strong>{engineLabel(latestReply?.engine_used)}</strong>
            </article>
          </div>

          {latestReply ? (
            <section className="chat-last-feedback stack">
              <h4>Last coach feedback</h4>
              {latestReply.corrections.length > 0 ? (
                latestReply.corrections.map((item, idx) => (
                  <article key={`${item.type}-${idx}`} className="chat-fix-item">
                    <small className="badge">{item.type}</small>
                    <p>
                      {item.bad} {"->"} {item.good}
                    </p>
                    {item.explanation && <small>{item.explanation}</small>}
                  </article>
                ))
              ) : (
                <p className="chat-empty">No corrections in last turn.</p>
              )}

              {latestReply.rubric && (
                <div className="chat-rubric-kpi">
                  <p>
                    Overall: {latestReply.rubric.overall_score}/100 ({latestReply.rubric.level_band})
                  </p>
                  <p>Grammar: {latestReply.rubric.grammar_accuracy.score}/5</p>
                  <p>Lexical: {latestReply.rubric.lexical_range.score}/5</p>
                </div>
              )}
            </section>
          ) : (
            <p className="chat-empty">Coach feedback will appear after your first message.</p>
          )}
        </aside>
      </section>
    </section>
  );
}
