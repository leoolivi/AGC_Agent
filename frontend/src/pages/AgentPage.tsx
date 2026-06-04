import { useState, useRef, useEffect, useCallback, type FormEvent } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { PanelLeftIcon } from "lucide-react";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  blocked?: boolean;
}

const markdownComponents: Components = {
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-border px-3 py-1.5 bg-muted text-left font-medium whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-border px-3 py-1.5 align-top">{children}</td>
  ),
};

export function AgentPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const activeIdRef = useRef<string | null>(null);
  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);

  const loadSessions = useCallback(async () => {
    try {
      const res = await api.get<ChatSession[]>("/api/v1/chat/sessions");
      setSessions(res.data);
      if (res.data.length > 0 && !activeIdRef.current) {
        setActiveId(res.data[0].id);
      }
    } catch {
    }
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  useEffect(() => {
    if (activeId) loadMessages(activeId);
    else setMessages([]);
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function loadMessages(sessionId: string) {
    try {
      const res = await api.get<Array<Omit<Message, "id"> & { id?: string }>>(
        `/api/v1/chat/sessions/${sessionId}/messages`
      );
      setMessages(res.data.map((m) => ({ ...m, id: m.id ?? crypto.randomUUID() })));
    } catch {
      setMessages([]);
    }
  }

  async function createSession() {
    try {
      const res = await api.post<ChatSession>("/api/v1/chat/sessions", { title: "Nuova chat" });
      setSessions((prev) => [res.data, ...prev]);
      setActiveId(res.data.id);
      setMessages([]);
    } catch {
      setError("Impossibile creare la sessione. Riprova.");
    }
  }

  async function deleteSession(id: string) {
    try {
      await api.delete(`/api/v1/chat/sessions/${id}`);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== id);
        setActiveId((currentId) =>
          currentId === id ? (remaining.length > 0 ? remaining[0].id : null) : currentId
        );
        return remaining;
      });
    } catch {
      setError("Impossibile eliminare la chat. Riprova.");
    }
  }

  async function renameSession(id: string, title: string) {
    try {
      await api.patch(`/api/v1/chat/sessions/${id}`, { title });
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
    } catch {
      setError("Impossibile rinominare la chat. Riprova.");
    }
    setEditingId(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading || !activeId) return;

    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<{ response: string; blocked: boolean }>(
        "/api/v1/agent/query",
        { message: msg, session_id: activeId }
      );
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "agent",
          content: res.data.response,
          blocked: res.data.blocked,
        },
      ]);
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeId && s.title === "Nuova chat"
            ? { ...s, title: msg.length > 80 ? `${msg.slice(0, 80)}…` : msg }
            : s
        )
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Errore di connessione";
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "agent", content: `Errore: ${errorMsg}. Riprova.` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-full flex flex-col">
      {error && (
        <div className="mb-2 flex items-center justify-between rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-4 font-bold">✕</button>
        </div>
      )}

      <div className="flex flex-1 gap-4 overflow-hidden">
        {isSidebarVisible && (
          <div className="w-56 flex-shrink-0 flex flex-col border-r pr-4 overflow-hidden">
            <div className="flex items-center gap-2 mb-3">
              <Button onClick={() => setIsSidebarVisible(false)} variant="ghost" size="sm" className="p-1">
                <PanelLeftIcon />
              </Button>
              <Button onClick={createSession} className="flex-1" size="sm">
                + Nuova chat
              </Button>
            </div>
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
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingId(s.id);
                          setEditTitle(s.title);
                        }}
                        title="Rinomina"
                      >
                        ✏️
                      </button>
                      <button
                        className="opacity-0 group-hover:opacity-100 text-xs px-1 text-destructive"
                        onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                        title="Elimina"
                      >
                        🗑️
                      </button>
                    </>
                  )}
                </div>
              ))}
              {sessions.length === 0 && (
                <p className="text-xs text-muted-foreground px-2">Nessuna chat. Creane una!</p>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="flex items-center gap-2 mb-4">
            {!isSidebarVisible && (
              <Button onClick={() => setIsSidebarVisible(true)} variant="ghost" size="sm" className="p-1">
                <PanelLeftIcon />
              </Button>
            )}
            <h2 className="text-xl font-semibold">Chat Agent</h2>
          </div>

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
                {messages.map((msg) => (
                  <Card key={msg.id} className={msg.role === "user" ? "ml-12" : "mr-12"}>
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium">
                          {msg.role === "user" ? "Tu" : "ACG"}
                        </span>
                        {msg.blocked && (
                          <Badge className="bg-destructive text-white">Bloccato</Badge>
                        )}
                      </div>
                      <div className="text-sm prose prose-sm max-w-none overflow-hidden">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={markdownComponents}
                        >
                          {msg.content}
                        </ReactMarkdown>
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

              <form onSubmit={handleSubmit} className="flex gap-2 shrink-0">
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
    </div>
  );
}