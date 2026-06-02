import { useState } from "react";
import { AdaptiveCanvas } from "./AdaptiveCanvas";
import { ConfidenceIndicator } from "@/components/shared/ConfidenceIndicator";

interface Clause {
  id: string;
  category: string;
  severity: string;
  clause_text: string;
  page_number?: number;
  plain_language_explanation: string;
  confidence_score: number;
}

interface ContractAnalysisCanvasProps {
  documentContent: string;
  clauses: Clause[];
}

const severityOrder = { alto: 0, medio: 1, basso: 2 };

export function ContractAnalysisCanvas({ documentContent, clauses }: ContractAnalysisCanvasProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const grouped = clauses.reduce<Record<string, Clause[]>>((acc, c) => {
    (acc[c.category] ??= []).push(c);
    return acc;
  }, {});

  const sorted = [...clauses].sort(
    (a, b) =>
      (severityOrder[a.severity as keyof typeof severityOrder] ?? 2) -
      (severityOrder[b.severity as keyof typeof severityOrder] ?? 2)
  );

  const selected = clauses.find((c) => c.id === selectedId);

  return (
    <AdaptiveCanvas
      context="contract"
      main={
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">
          {documentContent || "Anteprima documento"}
          {selected && (
            <mark className="bg-yellow-200 block mt-4 p-2 rounded">
              {selected.clause_text}
            </mark>
          )}
        </div>
      }
      side={
        clauses.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nessuna clausola rischiosa rilevata.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <h3 className="text-sm font-semibold capitalize">{cat.replace(/_/g, " ")}</h3>
                {items
                  .sort((a, b) => (severityOrder[a.severity as keyof typeof severityOrder] ?? 2) - (severityOrder[b.severity as keyof typeof severityOrder] ?? 2))
                  .map((c) => (
                    <button
                      key={c.id}
                      onClick={() => setSelectedId(c.id)}
                      className={`block w-full text-left p-2 mt-1 rounded text-sm border ${
                        selectedId === c.id ? "border-primary bg-accent" : "border-transparent hover:bg-accent"
                      }`}
                    >
                      <span className="font-medium capitalize">{c.severity}</span>
                      <p className="text-xs text-muted-foreground truncate">{c.plain_language_explanation}</p>
                      <ConfidenceIndicator score={c.confidence_score} />
                    </button>
                  ))}
              </div>
            ))}
          </div>
        )
      }
    />
  );
}
