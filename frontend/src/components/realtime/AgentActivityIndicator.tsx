import { useState } from "react";
import { useRealtimeStore } from "@/store/realtime";
import { useConfirmations } from "@/api/hooks";
import { Activity, ChevronDown, ChevronUp } from "lucide-react";

type AgentState = "inactive" | "monitoring" | "processing" | "needs_attention";

function deriveState(
  feedLen: number,
  pendingConfs: number,
  hasSources: boolean
): AgentState {
  if (pendingConfs > 0) return "needs_attention";
  if (feedLen > 0) return "processing";
  if (hasSources) return "monitoring";
  return "inactive";
}

const stateLabels: Record<AgentState, string> = {
  inactive: "Inattivo",
  monitoring: "Monitoraggio attivo",
  processing: "Elaborazione in corso",
  needs_attention: "Richiede attenzione",
};

const stateColors: Record<AgentState, string> = {
  inactive: "bg-gray-400",
  monitoring: "bg-blue-500",
  processing: "bg-amber-500",
  needs_attention: "bg-red-500",
};

export function AgentActivityIndicator() {
  const [expanded, setExpanded] = useState(false);
  const feed = useRealtimeStore((s) => s.processingFeed);
  const { data: confirmations } = useConfirmations();
  const pending = confirmations?.length ?? 0;
  const state = deriveState(feed.length, pending, true);
  const todayCount = feed.filter(
    (i) => i.status === "completed" && Date.now() - i.timestamp < 86400000
  ).length;

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs hover:bg-accent"
      >
        <span className={`h-2 w-2 rounded-full ${stateColors[state]}`} />
        Agent
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>
      {expanded && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-background border rounded-lg shadow-lg p-3 z-50">
          <p className="text-sm font-medium flex items-center gap-2">
            <Activity className="h-4 w-4" />
            {stateLabels[state]}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Documenti elaborati oggi: {todayCount}
          </p>
          {feed.slice(0, 5).map((i) => (
            <p key={i.id} className="text-xs truncate mt-1">{i.filename} — {i.status}</p>
          ))}
          {pending > 0 && (
            <a href="/confirmations" className="text-xs text-primary underline mt-2 block">
              {pending} conferme in attesa
            </a>
          )}
        </div>
      )}
    </div>
  );
}
