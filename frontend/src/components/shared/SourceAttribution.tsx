import { ConfidenceIndicator } from "@/components/shared/ConfidenceIndicator";

interface SourceAttributionProps {
  documentName?: string;
  documentId?: string;
  passage?: string;
  page?: number;
  confidence?: number;
}

export function SourceAttribution({
  documentName,
  documentId,
  passage,
  page,
  confidence,
}: SourceAttributionProps) {
  if (!documentId && !documentName) {
    return <span className="text-xs text-muted-foreground italic">Suggerimento euristico</span>;
  }

  return (
    <div className="text-xs text-muted-foreground mt-1">
      {documentId ? (
        <a href={`/documents/${documentId}`} className="text-primary underline">
          {documentName ?? "Documento sorgente"}
        </a>
      ) : (
        <span>{documentName}</span>
      )}
      {page != null && <span> — pag. {page}</span>}
      {passage && <p className="mt-0.5 italic truncate">"{passage}"</p>}
      {confidence != null && <ConfidenceIndicator score={confidence} />}
    </div>
  );
}
