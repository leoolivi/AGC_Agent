import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
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

  const sendMessage = useMutation({
    mutationFn: async (message: string) => {
      const res = await api.post<{ response: string; workflow_id: string | null; blocked: boolean }>(
        "/api/v1/agent/query",
        { message }
      );
      return res.data;
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: "agent", content: data.response, workflow_id: data.workflow_id, blocked: data.blocked },
      ]);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    sendMessage.mutate(input);
    setInput("");
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
              <p className="text-sm">{msg.content}</p>
            </CardContent>
          </Card>
        ))}
        {sendMessage.isPending && (
          <p className="text-sm text-muted-foreground">Elaborazione...</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Scrivi un messaggio..."
          className="flex-1"
        />
        <Button type="submit" disabled={sendMessage.isPending}>Invia</Button>
      </form>
    </div>
  );
}
