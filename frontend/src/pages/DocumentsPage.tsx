import { useState, useCallback, useRef, type DragEvent } from "react";
import { Upload, FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useDocuments, useUploadDocument } from "@/api/hooks";

const ACCEPTED_TYPES = new Set([
  "application/pdf",
  "text/csv",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]);
const MAX_SIZE = 20 * 1024 * 1024;

function DocumentUploadZone() {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const upload = useUploadDocument();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError("");
      if (!ACCEPTED_TYPES.has(file.type)) {
        setError("Formato non supportato. Usa PDF, XLSX, XLS o CSV.");
        return;
      }
      if (file.size > MAX_SIZE) {
        setError("File troppo grande. Massimo 20MB.");
        return;
      }
      upload.mutate(file);
    },
    [upload]
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragging ? "border-primary bg-primary/5" : "border-border"
      }`}
    >
      <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
      {upload.isPending ? (
        <p className="text-sm text-muted-foreground">Caricamento in corso...</p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Trascina un file qui o{" "}
          <button className="text-primary underline" onClick={() => inputRef.current?.click()}>
            seleziona
          </button>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".pdf,.csv,.xls,.xlsx"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
        </p>
      )}
      <p className="text-xs text-muted-foreground mt-1">PDF, XLSX, XLS, CSV — max 20MB</p>
      {error && <p className="text-sm text-destructive mt-2">{error}</p>}
      {upload.isError && <p className="text-sm text-destructive mt-2">Errore durante l'upload</p>}
      {upload.isSuccess && <p className="text-sm text-success mt-2">Documento caricato!</p>}
    </div>
  );
}

const statusBadge: Record<string, string> = {
  parsed: "bg-success/10 text-success",
  pending: "bg-warning/10 text-warning",
  failed: "bg-destructive/10 text-destructive",
};

export function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments();

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Documenti</h2>
      <DocumentUploadZone />
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      <div className="space-y-2">
        {documents?.map((doc) => (
          <Card key={doc.id}>
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{doc.filename}</p>
                  <p className="text-xs text-muted-foreground">{doc.created_at?.split("T")[0]}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {doc.document_type && <Badge variant="secondary">{doc.document_type}</Badge>}
                <Badge className={statusBadge[doc.parse_status] || ""}>{doc.parse_status}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
        {documents && documents.length === 0 && (
          <p className="text-sm text-muted-foreground">Nessun documento caricato.</p>
        )}
      </div>
    </div>
  );
}
