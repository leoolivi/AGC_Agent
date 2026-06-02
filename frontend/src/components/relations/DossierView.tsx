interface MissingItem {
  description: string;
  certainty: string;
}

interface DossierDocument {
  document_id: string;
  role?: string;
}

interface DossierViewProps {
  title: string;
  completenessStatus: string;
  missingItems: MissingItem[];
  documents: DossierDocument[];
}

export function DossierView({ title, completenessStatus, missingItems, documents }: DossierViewProps) {
  const pct = completenessStatus === "complete" ? 100 : Math.max(0, 100 - missingItems.length * 20);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary transition-all duration-200" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Completezza: {completenessStatus === "complete" ? "Completo" : "Incompleto"}
        </p>
      </div>

      <div>
        <h3 className="text-sm font-medium">Documenti ({documents.length})</h3>
        <ul className="mt-2 space-y-1">
          {documents.map((d) => (
            <li key={d.document_id}>
              <a href={`/documents/${d.document_id}`} className="text-sm text-primary underline">
                {d.role ?? "Documento"} — {d.document_id.slice(0, 8)}...
              </a>
            </li>
          ))}
        </ul>
      </div>

      {missingItems.length > 0 && (
        <div>
          <h3 className="text-sm font-medium">Elementi mancanti</h3>
          <ul className="mt-2 space-y-2">
            {missingItems.map((m) => (
              <li key={m.description} className="flex items-center justify-between text-sm border rounded p-2">
                <span>{m.description}</span>
                <span className="text-xs text-muted-foreground capitalize">{m.certainty}</span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2 mt-3">
            <button className="text-xs px-3 py-1.5 border rounded hover:bg-accent">Cerca in Drive</button>
            <button className="text-xs px-3 py-1.5 border rounded hover:bg-accent">Richiedi al fornitore</button>
          </div>
        </div>
      )}
    </div>
  );
}
