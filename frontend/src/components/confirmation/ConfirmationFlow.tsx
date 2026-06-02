import { useState } from "react";
import type { Confirmation } from "@/api/types";
import { SourceAttribution } from "@/components/shared/SourceAttribution";
import { Button } from "@/components/ui/button";
import { useApproveConfirmation, useRejectConfirmation } from "@/api/hooks";

interface ConfirmationFlowProps {
  confirmation: Confirmation;
  onComplete?: () => void;
}

export function ConfirmationFlow({ confirmation, onComplete }: ConfirmationFlowProps) {
  const approve = useApproveConfirmation();
  const reject = useRejectConfirmation();
  const [confirmed, setConfirmed] = useState(false);
  const [editedPreview, setEditedPreview] = useState<Record<string, unknown>>(
    (confirmation.data_for_review?.preview as Record<string, unknown>) ?? {}
  );

  const risk = parseInt(confirmation.risk_level, 10);
  const borderClass =
    risk >= 4 ? "border-red-500 border-2" : risk >= 3 ? "border-yellow-400 border-2" : "border-border";

  const actionType = confirmation.data_for_review?.action_type as string | undefined;
  const sourceAttr = confirmation.data_for_review?.source_attribution as Record<string, string> | undefined;

  const handleApprove = async () => {
    if (risk >= 4 && !confirmed) {
      setConfirmed(true);
      return;
    }
    await approve.mutateAsync(confirmation.id);
    onComplete?.();
  };

  return (
    <div className={`rounded-lg border p-4 ${borderClass}`}>
      <header className="mb-3">
        <p className="text-xs text-muted-foreground uppercase">{actionType?.replace(/_/g, " ") ?? "Conferma"}</p>
        <h3 className="font-medium">{confirmation.description}</h3>
      </header>

      <div className="bg-muted/50 rounded p-3 text-sm space-y-2 mb-3">
        {Object.entries(editedPreview).map(([key, val]) => (
          <label key={key} className="block">
            <span className="text-xs text-muted-foreground capitalize">{key}</span>
            <input
              className="w-full border rounded px-2 py-1 mt-0.5 text-sm bg-background"
              value={String(val ?? "")}
              onChange={(e) => setEditedPreview({ ...editedPreview, [key]: e.target.value })}
            />
          </label>
        ))}
        {sourceAttr && (
          <SourceAttribution
            documentId={sourceAttr.document_id ?? sourceAttr.deadline_id}
            documentName={sourceAttr.deadline_title ?? sourceAttr.template}
          />
        )}
      </div>

      <footer className="flex gap-2 justify-end">
        <Button variant="outline" size="sm" onClick={() => reject.mutate({ id: confirmation.id })}>
          Annulla
        </Button>
        <Button size="sm" onClick={handleApprove} disabled={approve.isPending}>
          {risk >= 4 && !confirmed ? "Conferma definitiva" : "Approva"}
        </Button>
      </footer>

      {(approve.isSuccess || reject.isSuccess) && (
        <p className="text-xs text-green-600 mt-2">Operazione completata.</p>
      )}
    </div>
  );
}
