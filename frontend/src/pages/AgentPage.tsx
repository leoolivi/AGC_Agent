import { useState, useRef, useEffect, type FormEvent } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";

interface Message {
  role: "user" | "agent";
  content: string;
  workflow_id?: string | null;
  blocked?: boolean;
}

export function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<{ response: string; workflow_id: string | null; blocked: boolean }>(
        "/api/v1/agent/query",
        { message: msg }
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: res.data.response,
          workflow_id: res.data.workflow_id,
          blocked: res.data.blocked,
        },
      ]);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Errore di connessione";
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: `Errore: ${errorMsg}. Riprova.`, blocked: false },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold mb-4">Chat Agent</h2>

      <div className="flex-1 overflow-auto space-y-3 mb-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground">Scrivi un messaggio per iniziare.</p>
        )}
        {messages.map((msg, i) => (
          <Card key={i} className={msg.role === "user" ? "ml-12" : "mr-12"}>
            <CardContent className="p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium">{msg.role === "user" ? "Tu" : "ACG"}</span>
                {msg.workflow_id && <Badge variant="secondary">{msg.workflow_id}</Badge>}
                {msg.blocked && <Badge className="bg-destructive text-white">Bloccato</Badge>}
              </div>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </CardContent>
          </Card>
        ))}
        {loading && (
          <Card className="mr-12">
            <CardContent className="p-3">
              <p className="text-sm text-muted-foreground animate-pulse">ACG sta pensando...</p>
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
    </div>
  );
}
