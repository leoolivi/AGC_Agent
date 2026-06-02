import { AlertCircle, FileQuestion, Settings, User } from "lucide-react";
import { Button } from "@/components/ui/button";

type ErrorCategory = "technical" | "missing_data" | "needs_human_input";

interface ErrorStateProps {
  category: ErrorCategory;
  message: string;
  onRetry?: () => void;
  actionLabel?: string;
  onAction?: () => void;
}

const config: Record<ErrorCategory, { icon: typeof Settings; color: string; title: string }> = {
  technical: { icon: Settings, color: "text-red-600", title: "Errore tecnico" },
  missing_data: { icon: FileQuestion, color: "text-yellow-600", title: "Dati mancanti" },
  needs_human_input: { icon: User, color: "text-blue-600", title: "Input richiesto" },
};

export function ErrorState({ category, message, onRetry, actionLabel, onAction }: ErrorStateProps) {
  const { icon: Icon, color, title } = config[category];

  return (
    <div className="flex flex-col items-center text-center p-8 border rounded-lg">
      <Icon className={`h-10 w-10 ${color} mb-3`} />
      <h3 className="font-medium">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1 max-w-md">{message}</p>
      <div className="flex gap-2 mt-4">
        {onRetry && <Button size="sm" variant="outline" onClick={onRetry}>Riprova</Button>}
        {onAction && actionLabel && <Button size="sm" onClick={onAction}>{actionLabel}</Button>}
      </div>
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center p-8">
      <AlertCircle className="h-10 w-10 text-muted-foreground mb-3" />
      <h3 className="font-medium">{title}</h3>
      <p className="text-sm text-muted-foreground mt-1">{description}</p>
      {actionLabel && onAction && (
        <Button size="sm" className="mt-4" onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  );
}
