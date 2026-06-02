import { useEffect, useState } from "react";
import type { ConnectionState } from "@/hooks/useWebSocket";

interface ConnectionStatusProps {
  state: ConnectionState;
}

export function ConnectionStatus({ state }: ConnectionStatusProps) {
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    if (state === "disconnected") {
      const t = setTimeout(() => setShowBanner(true), 5000);
      return () => clearTimeout(t);
    }
    setShowBanner(false);
  }, [state]);

  const colors = {
    connected: "bg-green-500",
    reconnecting: "bg-yellow-500",
    disconnected: "bg-red-500",
  };

  const labels = {
    connected: "Connesso",
    reconnecting: "Riconnessione...",
    disconnected: "Disconnesso",
  };

  return (
    <>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className={`h-2 w-2 rounded-full ${colors[state]}`} />
        {labels[state]}
      </div>
      {showBanner && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-yellow-100 text-yellow-900 text-center py-2 text-sm">
          Connessione in corso...
        </div>
      )}
    </>
  );
}
