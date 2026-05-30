import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConfirmations, useApproveConfirmation, useRejectConfirmation } from "@/api/hooks";
import type { Confirmation } from "@/api/types";
import { useState } from "react";

function ReviewCard({ confirmation }: { confirmation: Confirmation }) {
  const approve = useApproveConfirmation();
  const reject = useRejectConfirmation();
  const [comment, setComment] = useState("");

  const data = confirmation.data_for_review || {};
  const fields = Object.entries(data);

  return (
    <Card className="border-l-4 border-l-warning">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Badge variant="secondary">Rischio {confirmation.risk_level}</Badge>
          <span className="text-xs text-muted-foreground">
            {confirmation.created_at?.split("T")[0]}
          </span>
        </div>
        <p className="text-sm">{confirmation.description}</p>

        {fields.length > 0 && (
          <div className="space-y-1 text-sm bg-muted/50 rounded p-3">
            {fields.map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-muted-foreground">{key}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 items-center">
          <Button
            size="sm"
            disabled={approve.isPending}
            onClick={() => approve.mutate(confirmation.id)}
          >
            Conferma
          </Button>
          <Input
            placeholder="Motivo rifiuto (opzionale)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="h-8 text-sm flex-1"
          />
          <Button
            size="sm"
            variant="destructive"
            disabled={reject.isPending}
            onClick={() => reject.mutate({ id: confirmation.id, comment })}
          >
            Rifiuta
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function ConfirmationsPage() {
  const { data: confirmations, isLoading } = useConfirmations();

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Conferme Pendenti</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {confirmations && confirmations.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna conferma pendente.</p>
      )}
      {confirmations?.map((c) => <ReviewCard key={c.id} confirmation={c} />)}
    </div>
  );
}
