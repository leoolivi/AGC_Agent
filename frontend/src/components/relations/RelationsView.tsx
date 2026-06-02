import { ConfidenceIndicator } from "@/components/shared/ConfidenceIndicator";
import { SourceAttribution } from "@/components/shared/SourceAttribution";

interface Correlation {
  id: string;
  target_document_id: string;
  correlation_type: string;
  confidence_score: number;
  confidence_level: string;
  source_passage?: string;
}

interface RelationsViewProps {
  documentId: string;
  documentName: string;
  correlations: Correlation[];
}

export function RelationsView({ documentId, documentName, correlations }: RelationsViewProps) {
  if (correlations.length === 0) {
    return <p className="text-sm text-muted-foreground">Nessuna relazione rilevata.</p>;
  }

  return (
    <ul className="space-y-3">
      {correlations.map((c) => (
        <li key={c.id} className="border rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium capitalize">{c.correlation_type.replace(/_/g, " ")}</span>
            <ConfidenceIndicator score={c.confidence_score} />
          </div>
          <SourceAttribution
            documentName={documentName}
            documentId={documentId}
            passage={c.source_passage}
            confidence={c.confidence_score}
          />
          <a href={`/documents/${c.target_document_id}`} className="text-xs text-primary underline mt-1 block">
            Vai al documento correlato
          </a>
        </li>
      ))}
    </ul>
  );
}
