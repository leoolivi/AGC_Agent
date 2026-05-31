import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/api/client";

interface Draft {
  id: string;
  subject: string;
  to_addresses: string[];
  body_html: string;
  body_text: string;
  status: string;
  created_at: string | null;
}

const statusConfig: Record<string, { label: string; class: string }> = {
  pending_review: { label: "Da revisionare", class: "bg-warning/10 text-warning" },
  approved: { label: "Approvata", class: "bg-success/10 text-success" },
  sent: { label: "Inviata", class: "bg-muted text-muted-foreground" },
};

function DraftCard({ draft, onSelect }: { draft: Draft; onSelect: () => void }) {
  const cfg = statusConfig[draft.status] || { label: draft.status, class: "" };
  return (
    <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={onSelect}>
      <CardContent className="p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">{draft.subject}</p>
          <p className="text-xs text-muted-foreground">A: {draft.to_addresses.join(", ")}</p>
        </div>
        <Badge className={cfg.class}>{cfg.label}</Badge>
      </CardContent>
    </Card>
  );
}

function DraftDetail({ draft, onBack }: { draft: Draft; onBack: () => void }) {
  const qc = useQueryClient();
  const [subject, setSubject] = useState(draft.subject);
  const [to, setTo] = useState(draft.to_addresses.join(", "));
  const [body, setBody] = useState(draft.body_text);
  const [editing, setEditing] = useState(false);

  const updateDraft = useMutation({
    mutationFn: async () => {
      await api.put(`/api/v1/email-drafts/${draft.id}`, {
        subject,
        to_addresses: to.split(",").map((s) => s.trim()),
        body_text: body,
        body_html: `<p>${body.replace(/\n/g, "<br>")}</p>`,
      });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["email-drafts"] }); setEditing(false); },
  });

  const approveDraft = useMutation({
    mutationFn: async () => { await api.post(`/api/v1/email-drafts/${draft.id}/approve`); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["email-drafts"] }); onBack(); },
  });

  const deleteDraft = useMutation({
    mutationFn: async () => { await api.delete(`/api/v1/email-drafts/${draft.id}`); },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["email-drafts"] }); onBack(); },
  });

  const isEditable = draft.status === "pending_review";

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" onClick={onBack}>← Torna alla lista</Button>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Bozza Email</CardTitle>
            <Badge className={statusConfig[draft.status]?.class || ""}>
              {statusConfig[draft.status]?.label || draft.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {editing ? (
            <>
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Destinatario</label>
                <Input value={to} onChange={(e) => setTo(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Oggetto</label>
                <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Corpo</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={10}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => updateDraft.mutate()} disabled={updateDraft.isPending}>
                  Salva modifiche
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Annulla</Button>
              </div>
            </>
          ) : (
            <>
              <div className="text-sm space-y-1">
                <p><span className="text-muted-foreground">A:</span> {draft.to_addresses.join(", ")}</p>
                <p><span className="text-muted-foreground">Oggetto:</span> <strong>{draft.subject}</strong></p>
              </div>
              <div className="bg-muted/50 rounded-md p-4 text-sm whitespace-pre-wrap">
                {draft.body_text}
              </div>
            </>
          )}

          {isEditable && !editing && (
            <div className="flex gap-2 pt-2 border-t">
              <Button size="sm" onClick={() => approveDraft.mutate()} disabled={approveDraft.isPending}>
                ✓ Approva e invia
              </Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                ✏️ Modifica
              </Button>
              <Button size="sm" variant="destructive" onClick={() => deleteDraft.mutate()} disabled={deleteDraft.isPending}>
                ✗ Elimina
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function EmailDraftsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: drafts, isLoading } = useQuery<Draft[]>({
    queryKey: ["email-drafts"],
    queryFn: async () => {
      const res = await api.get<Draft[]>("/api/v1/email-drafts");
      return res.data;
    },
  });

  // Fetch full draft when selected
  const { data: selectedDraft } = useQuery<Draft>({
    queryKey: ["email-drafts", selectedId],
    queryFn: async () => (await api.get<Draft>(`/api/v1/email-drafts/${selectedId}`)).data,
    enabled: !!selectedId,
  });

  if (selectedId && selectedDraft) {
    return <DraftDetail draft={selectedDraft} onBack={() => setSelectedId(null)} />;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Bozze Email</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {drafts && drafts.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna bozza email. Chiedi all'agente di prepararne una.</p>
      )}
      {drafts?.map((d) => (
        <DraftCard key={d.id} draft={d} onSelect={() => setSelectedId(d.id)} />
      ))}
    </div>
  );
}
