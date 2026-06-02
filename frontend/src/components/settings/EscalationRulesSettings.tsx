import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";

interface EscalationRule {
  id: string;
  name: string;
  deadline_type: string;
  steps: Array<{ delay_seconds: number; channel: string; recipient: string; message_template: string }>;
  is_active: boolean;
}

const TEMPLATES = [
  { name: "Standard fiscale", deadline_type: "fiscale", steps: [{ delay_seconds: 86400, channel: "in_app", recipient: "user", message_template: "Scadenza: {deadline_title}" }] },
];

export function EscalationRulesSettings() {
  const qc = useQueryClient();
  const { data: rules = [] } = useQuery<EscalationRule[]>({
    queryKey: ["escalation-rules"],
    queryFn: async () => (await api.get("/api/v1/escalation-rules")).data,
  });

  const createRule = useMutation({
    mutationFn: (rule: typeof TEMPLATES[0]) => api.post("/api/v1/escalation-rules", rule),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["escalation-rules"] }),
  });

  const [builder, setBuilder] = useState<typeof TEMPLATES[0] | null>(null);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Regole Escalation</h2>

      <div className="flex gap-2 flex-wrap">
        {TEMPLATES.map((t) => (
          <Button key={t.name} size="sm" variant="outline" onClick={() => setBuilder(t)}>
            {t.name}
          </Button>
        ))}
      </div>

      {builder && (
        <div className="border rounded-lg p-4 space-y-3">
          <h3 className="font-medium">Anteprima flusso</h3>
          <ol className="relative border-l ml-3 space-y-4">
            {builder.steps.map((s, i) => (
              <li key={i} className="ml-4">
                <span className="absolute -left-1.5 h-3 w-3 rounded-full bg-primary" />
                <p className="text-sm">Step {i + 1}: {s.channel} dopo {Math.round(s.delay_seconds / 3600)}h</p>
              </li>
            ))}
          </ol>
          <Button size="sm" onClick={() => createRule.mutate(builder)}>Salva regola</Button>
        </div>
      )}

      <ul className="space-y-2">
        {rules.map((r) => (
          <li key={r.id} className="border rounded-lg p-3">
            <p className="font-medium">{r.name}</p>
            <p className="text-xs text-muted-foreground">{r.deadline_type} — {r.steps.length} step</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
