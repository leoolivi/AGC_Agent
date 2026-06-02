import { RelationsView } from "@/components/relations/RelationsView";
import { DossierView } from "@/components/relations/DossierView";
import { EmptyState } from "@/components/errors/ErrorEmptyStates";

export function RelationsPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Relazioni</h1>
      <section>
        <h2 className="text-lg font-medium mb-3">Correlazioni documento</h2>
        <EmptyState
          title="Seleziona un documento"
          description="Apri un documento per vedere le sue relazioni cross-document."
          actionLabel="Vai ai documenti"
          onAction={() => { window.location.href = "/documents"; }}
        />
      </section>
      <section>
        <h2 className="text-lg font-medium mb-3">Fascicoli</h2>
        <DossierView title="Esempio fascicolo" completenessStatus="incomplete" missingItems={[]} documents={[]} />
      </section>
    </div>
  );
}
