import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/client";

interface Draft {
  id: string;
  subject: string;
  to_addresses: string[];
  status: string;
  created_at: string | null;
}

const statusColor: Record<string, string> = {
  pending_review: "bg-warning/10 text-warning",
  approved: "bg-success/10 text-success",
  sent: "bg-muted text-muted-foreground",
};

export function EmailDraftsPage() {
  const { data: drafts, isLoading } = useQuery<Draft[]>({
    queryKey: ["email-drafts"],
    queryFn: async () => (await api.get<Draft[]>("/api/v1/email-drafts")).data,
  });

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Bozze Email</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {drafts && drafts.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna bozza email.</p>
      )}
      {drafts?.map((d) => (
        <Card key={d.id}>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{d.subject}</p>
              <p className="text-xs text-muted-foreground">A: {d.to_addresses.join(", ")}</p>
            </div>
            <Badge className={statusColor[d.status] || ""}>{d.status}</Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
