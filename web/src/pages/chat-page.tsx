import { FormEvent, useState } from "react";
import { api } from "../api/client";
import type { ChatMessageResponse } from "../api/types";
import { useAppStore } from "../store/app-store";

export function ChatPage() {
  const userId = useAppStore((s) => s.userId) ?? 1;
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [text, setText] = useState("I goed to school today");
  const [reply, setReply] = useState<ChatMessageResponse | null>(null);
  const [status, setStatus] = useState("");

  async function onStart() {
    const response = await api.chatStart({ user_id: userId, mode: "chat" });
    setSessionId(response.session_id);
    setStatus(`Session ${response.session_id} started`);
  }

  async function onSend(event: FormEvent) {
    event.preventDefault();
    if (!sessionId) return;
    const response = await api.chatMessage({ session_id: sessionId, text });
    setReply(response);
  }

  async function onEnd() {
    if (!sessionId) return;
    const response = await api.chatEnd({ session_id: sessionId });
    setStatus(`Session ${response.session_id} ${response.status}`);
    setSessionId(null);
  }

  return (
    <section className="panel stack">
      <h2>Teacher Chat</h2>
      <div className="row">
        <button type="button" onClick={onStart} disabled={!!sessionId}>
          Start session
        </button>
        <button type="button" onClick={onEnd} disabled={!sessionId}>
          End session
        </button>
      </div>
      {status && <p>{status}</p>}
      <form onSubmit={onSend} className="stack">
        <label>
          Message
          <input value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <button type="submit" disabled={!sessionId}>
          Send to teacher
        </button>
      </form>
      {reply && (
        <article className="panel">
          <p>{reply.assistant_text}</p>
          {reply.corrections.map((c, idx) => (
            <p key={`${c.type}-${idx}`}>
              {c.bad} {"->"} {c.good}
            </p>
          ))}
        </article>
      )}
    </section>
  );
}
