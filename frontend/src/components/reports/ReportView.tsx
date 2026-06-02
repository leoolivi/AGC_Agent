import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { AdaptiveCanvas } from "@/components/canvas/AdaptiveCanvas";

export function ReportView() {
  const [dateFrom, setDateFrom] = useState("2026-01-01");
  const [dateTo, setDateTo] = useState("2026-12-31");
  const [template, setTemplate] = useState("scadenze_mensili");
  const [format, setFormat] = useState<"pdf" | "excel">("pdf");
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);

  const { data: templates = [] } = useQuery({
    queryKey: ["report-templates"],
    queryFn: async () => (await api.get("/api/v1/reports/templates")).data,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["report-history"],
    queryFn: async () => (await api.get("/api/v1/reports/history")).data,
  });

  const generate = useMutation({
    mutationFn: async () => {
      const res = await api.post("/api/v1/reports", {
        template_name: template,
        date_from: dateFrom,
        date_to: dateTo,
        format,
      });
      return res.data;
    },
    onSuccess: (data) => setPreview(data),
  });

  return (
    <AdaptiveCanvas
      context="default"
      main={
        <div className="space-y-4 max-w-lg">
          <h2 className="text-lg font-semibold">Report</h2>
          <div className="grid gap-3">
            <label className="text-sm">
              Template
              <select className="w-full border rounded px-2 py-1 mt-1" value={template} onChange={(e) => setTemplate(e.target.value)}>
                {templates.map((t: { name: string; title: string }) => (
                  <option key={t.name} value={t.name}>{t.title ?? t.name}</option>
                ))}
              </select>
            </label>
            <div className="flex gap-2">
              <label className="text-sm flex-1">Da<input type="date" className="w-full border rounded px-2 py-1 mt-1" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
              <label className="text-sm flex-1">A<input type="date" className="w-full border rounded px-2 py-1 mt-1" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label>
            </div>
            <label className="text-sm">
              Formato
              <select className="w-full border rounded px-2 py-1 mt-1" value={format} onChange={(e) => setFormat(e.target.value as "pdf" | "excel")}>
                <option value="pdf">PDF</option>
                <option value="excel">Excel</option>
              </select>
            </label>
            <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
              Genera anteprima
            </Button>
          </div>
          {preview && (
            <div className="border rounded p-3 text-sm">
              <p>Righe: {(preview.preview_rows as unknown[])?.length ?? 0}</p>
              <div className="flex gap-2 mt-2">
                <Button size="sm" variant="outline">Esporta su Drive</Button>
                <Button size="sm" variant="outline">Invia via email</Button>
              </div>
            </div>
          )}
        </div>
      }
      side={
        <div>
          <h3 className="text-sm font-medium">Storico</h3>
          <ul className="mt-2 space-y-2">
            {(history as Array<{ id: string; template_name: string; created_at: string }>).map((h) => (
              <li key={h.id} className="text-xs border rounded p-2">
                {h.template_name} — {new Date(h.created_at).toLocaleDateString()}
              </li>
            ))}
          </ul>
        </div>
      }
    />
  );
}
