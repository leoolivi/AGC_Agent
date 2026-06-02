import { useConfirmations } from "@/api/hooks";
import { ConfirmationFlow } from "@/components/confirmation/ConfirmationFlow";

export function ConfirmationsPage() {
  const { data: confirmations, isLoading } = useConfirmations();

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Conferme Pendenti</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
      {confirmations && confirmations.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessuna conferma pendente.</p>
      )}
      {confirmations?.map((c) => (
        <ConfirmationFlow key={c.id} confirmation={c} />
      ))}
    </div>
  );
}
