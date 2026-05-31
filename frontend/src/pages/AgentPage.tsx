import { useState, useRef, useEffect, type FormEvent } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  id?: string;
  role: "user" | "agent";
  content: string;
  blocked?: boolean;
}

export function AgentPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load sessions on mount
  useEffect(() => { loadSessions(); }, []);

  // Load messages when active session changes
  useEffect(() => {
    if (activeId) loadMessages(activeId);
    else setMessages([]);
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function loadSessions() {
    try {
      const res = await api.get<ChatSession[]>("/api/v1/chat/sessions");
      setSessions(res.data);
      if (res.data.length > 0 && !activeId) setActiveId(res.data[0].id);
    } catch { /* ignore */ }
  }

  async function loadMessages(sessionId: string) {
    try {
      const res = await api.get<Message[]>(`/api/v1/chat/sessions/${sessionId}/messages`);
      setMessages(res.data);
    } catch { setMessages([]); }
  }

  async function createSession() {
    try {
      const res = await api.post<ChatSession>("/api/v1/chat/sessions", { title: "Nuova chat" });
      setSessions((prev) => [res.data, ...prev]);
      setActiveId(res.data.id);
      setMessages([]);
    } catch { /* ignore */ }
  }

  async function deleteSession(id: string) {
    try {
      await api.delete(`/api/v1/chat/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeId === id) {
        const remaining = sessions.filter((s) => s.id !== id);
        setActiveId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch { /* ignore */ }
  }

  async function renameSession(id: string, title: string) {
    try {
      await api.patch(`/api/v1/chat/sessions/${id}`, { title });
      setSessions((prev) => prev.map((s) => s.id === id ? { ...s, title } : s));
    } catch { /* ignore */ }
    setEditingId(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading || !activeId) return;

    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<{ response: string; blocked: boolean }>(
        "/api/v1/agent/query",
        { message: msg, session_id: activeId }
      );
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: res.data.response, blocked: res.data.blocked },
      ]);
      // Update session title in sidebar if it was auto-titled
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeId && s.title === "Nuova chat"
            ? { ...s, title: msg.slice(0, 80) }
            : s
        )
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Errore di connessione";
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: `Errore: ${errorMsg}. Riprova.` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full gap-4">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 flex flex-col border-r pr-4">
        <Button onClick={createSession} className="mb-3 w-full" size="sm">
          + Nuova chat
        </Button>
        <div className="flex-1 overflow-auto space-y-1">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center gap-1 rounded px-2 py-1.5 text-sm cursor-pointer ${
                s.id === activeId ? "bg-accent" : "hover:bg-muted"
              }`}
              onClick={() => setActiveId(s.id)}
            >
              {editingId === s.id ? (
                <Input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => renameSession(s.id, editTitle)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") renameSession(s.id, editTitle);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  className="h-6 text-xs"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <span className="flex-1 truncate">{s.title}</span>
                  <button
                    className="opacity-0 group-hover:opacity-100 text-xs px-1"
                    onClick={(e) => { e.stopPropagation(); setEditingId(s.id); setEditTitle(s.title); }}
                    title="Rinomina"
                  >✏️</button>
                  <button
                    className="opacity-0 group-hover:opacity-100 text-xs px-1 text-destructive"
                    onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                    title="Elimina"
                  >🗑️</button>
                </>
              )}
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-muted-foreground px-2">Nessuna chat. Creane una!</p>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <h2 className="text-xl font-semibold mb-4">Chat Agent</h2>

        {!activeId ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Seleziona o crea una chat per iniziare.</p>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto space-y-3 mb-4">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground">Scrivi un messaggio per iniziare.</p>
              )}
              {messages.map((msg, i) => (
                <Card key={msg.id || i} className={msg.role === "user" ? "ml-12" : "mr-12"}>
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium">
                        {msg.role === "user" ? "Tu" : "ACG"}
                      </span>
                      {msg.blocked && (
                        <Badge className="bg-destructive text-white">Bloccato</Badge>
                      )}
                    </div>
                    <div className="text-sm prose prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {loading && (
                <Card className="mr-12">
                  <CardContent className="p-3">
                    <p className="text-sm text-muted-foreground animate-pulse">
                      ACG sta pensando...
                    </p>
                  </CardContent>
                </Card>
              )}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Scrivi un messaggio..."
                className="flex-1"
                disabled={loading}
              />
              <Button type="submit" disabled={loading}>Invia</Button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
