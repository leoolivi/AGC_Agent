import { useRealtimeStore } from "@/store/realtime";
import { FileText, HardDrive, Mail, Calendar } from "lucide-react";

const sourceIcons: Record<string, typeof FileText> = {
  drive: HardDrive,
  gmail: Mail,
  calendar: Calendar,
  upload: FileText,
};

export function ProcessingFeed() {
  const feed = useRealtimeStore((s) => s.processingFeed);

  if (feed.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        Nessun documento in elaborazione
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto">
      {feed.map((item) => {
        const Icon = sourceIcons[item.source] ?? FileText;
        return (
          <div
            key={item.id}
            className={`flex items-center gap-3 p-3 rounded-lg border ${
              item.needsAttention ? "border-yellow-400 bg-yellow-50" : "border-border"
            }`}
          >
            <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{item.filename}</p>
              <p className="text-xs text-muted-foreground">{item.status}</p>
            </div>
            {item.needsAttention && (
              <a href={`/documents/${item.id}`} className="text-xs text-yellow-700 underline">
                Rivedi
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
