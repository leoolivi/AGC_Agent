import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/api/client";

interface Deadline {
  id: string;
  title: string;
  due_date: string;
  deadline_type: string;
  recurrence: string;
  status: string;
  source: string;
}

export function DeadlinesPage() {
  const qc = useQueryClient();
  const { data: deadlines, isLoading } = useQuery<Deadline[]>({
    queryKey: ["deadlines"],
    queryFn: async () => (await api.get<Deadline[]>("/api/v1/deadlines")).data,
  });

  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");

  const createDeadline = useMutation({
    mutationFn: async () => {
      await api.post("/api/v1/deadlines", { title, due_date: dueDate });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deadlines"] }); setTitle(""); setDueDate(""); },
  });

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (title && dueDate) createDeadline.mutate();
  }

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Scadenze</h2>

      <form onSubmit={handleCreate} className="flex gap-2">
        <Input placeholder="Titolo scadenza" value={title} onChange={(e) => setTitle(e.target.value)} className="flex-1" />
        <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="w-40" />
        <Button type="submit" disabled={createDeadline.isPending}>Crea</Button>
      </form>

      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {deadlines && deadlines.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna scadenza.</p>
      )}
      {deadlines?.map((d) => {
        const isOverdue = d.due_date < today && d.status === "active";
        return (
          <Card key={d.id} className={isOverdue ? "border-l-4 border-l-urgent" : ""}>
            <CardContent className="p-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{d.title}</p>
                <p className="text-xs text-muted-foreground">{d.due_date} • {d.deadline_type}</p>
              </div>
              <div className="flex gap-2">
                {d.recurrence !== "none" && <Badge variant="secondary">{d.recurrence}</Badge>}
                <Badge className={isOverdue ? "bg-urgent text-white" : "bg-success/10 text-success"}>
                  {isOverdue ? "Scaduta" : d.status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
