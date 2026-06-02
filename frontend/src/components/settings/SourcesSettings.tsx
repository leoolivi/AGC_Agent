import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";

interface Source {
  id: string;
  source_type: string;
  config: Record<string, unknown>;
  status: string;
  last_sync_at?: string;
}

export function SourcesSettings() {
  const qc = useQueryClient();
  const { data: sources = [] } = useQuery<Source[]>({
    queryKey: ["sources"],
    queryFn: async () => (await api.get("/api/v1/sources")).data,
  });

  const reconnect = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/sources/${id}/reconnect`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Sorgenti monitorate</h2>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>Aggiungi sorgente</Button>
      </div>

      {showForm && (
        <div className="border rounded-lg p-4 space-y-3">
          <p className="text-sm text-muted-foreground">
            Collega Google OAuth dalle impostazioni account, poi configura cartella Drive, label Gmail o calendario.
          </p>
        </div>
      )}

      <ul className="space-y-2">
        {sources.map((s) => (
          <li key={s.id} className="flex items-center justify-between border rounded-lg p-3">
            <div>
              <p className="text-sm font-medium capitalize">{s.source_type}</p>
              <p className="text-xs text-muted-foreground">
                Stato: {s.status} {s.last_sync_at && `— Ultimo sync: ${new Date(s.last_sync_at).toLocaleString()}`}
              </p>
            </div>
            {s.status === "error" && (
              <Button size="sm" variant="outline" onClick={() => reconnect.mutate(s.id)}>
                Riconnetti
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
