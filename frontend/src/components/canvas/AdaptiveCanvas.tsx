import { ReactNode, useState } from "react";
import { X } from "lucide-react";

interface ZoneProps {
  children: ReactNode;
  dismissKey?: string;
}

function Zone({ children, dismissKey }: ZoneProps) {
  const storageKey = dismissKey ? `canvas-dismiss-${dismissKey}` : undefined;
  const [visible, setVisible] = useState(() =>
    storageKey ? sessionStorage.getItem(storageKey) !== "hidden" : true
  );

  if (!visible) return null;

  return (
    <div className="relative transition-all duration-200">
      {dismissKey && (
        <button
          onClick={() => {
            setVisible(false);
            sessionStorage.setItem(storageKey!, "hidden");
          }}
          className="absolute top-2 right-2 p-1 rounded hover:bg-accent z-10"
          aria-label="Chiudi pannello"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      {children}
    </div>
  );
}

interface AdaptiveCanvasProps {
  context: "contract" | "deadlines" | "inbox" | "default";
  main: ReactNode;
  side?: ReactNode;
  bottom?: ReactNode;
}

export function AdaptiveCanvas({ context, main, side, bottom }: AdaptiveCanvasProps) {
  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex flex-1 gap-4 min-h-0">
        <div className="flex-1 min-w-0 overflow-auto transition-all duration-200">{main}</div>
        {side && (
          <Zone dismissKey={`side-${context}`}>
            <aside className="w-80 shrink-0 border rounded-lg p-4 overflow-auto transition-all duration-200">
              {side}
            </aside>
          </Zone>
        )}
      </div>
      {bottom && (
        <Zone dismissKey={`bottom-${context}`}>
          <div className="border rounded-lg p-4 max-h-48 overflow-auto transition-all duration-200">
            {bottom}
          </div>
        </Zone>
      )}
    </div>
  );
}
