import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";
import type { AuditEntry } from "@/api/types";

export function AuditPage() {
  const { data: entries, isLoading } = useQuery<AuditEntry[]>({
    queryKey: ["audit-log"],
    queryFn: async () => (await api.get<AuditEntry[]>("/api/v1/audit-log")).data,
  });

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Audit Log</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {entries && entries.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna voce nel log.</p>
      )}
      {entries?.map((e) => (
        <Card key={e.id}>
          <CardContent className="p-3 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{e.action_type}</Badge>
                {e.tool_name && <span className="text-xs text-muted-foreground">{e.tool_name}</span>}
              </div>
              {e.input_summary && <p className="text-xs text-muted-foreground mt-1">{e.input_summary}</p>}
            </div>
            <span className="text-xs text-muted-foreground">{e.created_at?.split("T")[0]}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
