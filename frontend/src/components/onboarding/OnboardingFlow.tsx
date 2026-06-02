import { useState } from "react";
import { Button } from "@/components/ui/button";

const STEPS = [
  { id: 1, title: "Collega le sorgenti", message: "Connetti Drive, Gmail o Calendar per l'import automatico." },
  { id: 2, title: "Importa un documento", message: "Carica o importa il tuo primo documento amministrativo." },
  { id: 3, title: "Rivedi una scadenza", message: "Controlla la scadenza proposta dall'agent." },
  { id: 4, title: "Configura le notifiche", message: "Imposta le regole di escalation per le scadenze." },
];

interface OnboardingFlowProps {
  onComplete?: () => void;
  onSkip?: () => void;
}

export function OnboardingFlow({ onComplete, onSkip }: OnboardingFlowProps) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];

  const next = () => {
    if (step >= STEPS.length - 1) {
      onComplete?.();
    } else {
      setStep(step + 1);
    }
  };

  return (
    <div className="max-w-md mx-auto border rounded-lg p-6 space-y-4">
      <div className="flex gap-1">
        {STEPS.map((s, i) => (
          <div key={s.id} className={`h-1 flex-1 rounded ${i <= step ? "bg-primary" : "bg-muted"}`} />
        ))}
      </div>
      <div className="bg-muted/50 rounded-lg p-4">
        <p className="text-xs text-muted-foreground">Agent ACG</p>
        <p className="text-sm mt-2">{current.message}</p>
      </div>
      <p className="text-sm font-medium">{current.title}</p>
      <div className="flex justify-between">
        <Button variant="ghost" size="sm" onClick={onSkip}>Salta</Button>
        <Button size="sm" onClick={next}>
          {step >= STEPS.length - 1 ? "Completa" : "Avanti"}
        </Button>
      </div>
    </div>
  );
}
