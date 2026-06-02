import { useState } from "react";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CalendarEvent {
  id: string;
  title: string;
  date: string;
  participants: string;
  tracked?: boolean;
  relevant?: boolean;
}

const MOCK_EVENTS: CalendarEvent[] = [
  { id: "e1", title: "Scadenza IVA Q1", date: "2026-04-16", participants: "admin@acg.it", relevant: true },
  { id: "e2", title: "Team lunch", date: "2026-04-20", participants: "team@acg.it", relevant: false },
  { id: "e3", title: "Rinnovo contratto fornitore", date: "2026-05-01", participants: "legal@acg.it", tracked: true, relevant: true },
];

export function CalendarQuickView() {
  const [hideIrrelevant, setHideIrrelevant] = useState(true);

  const events = MOCK_EVENTS
    .filter((e) => !hideIrrelevant || e.relevant !== false)
    .sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          <h3 className="font-medium text-sm">Calendario — 30 giorni</h3>
        </div>
        <label className="text-xs flex items-center gap-1">
          <input type="checkbox" checked={hideIrrelevant} onChange={(e) => setHideIrrelevant(e.target.checked)} />
          Solo amministrativi
        </label>
      </div>
      <ul className="space-y-2 max-h-64 overflow-y-auto">
        {events.map((e) => (
          <li key={e.id} className="border rounded p-2 text-sm">
            <p className="font-medium">{e.title}</p>
            <p className="text-xs text-muted-foreground">{e.date} — {e.participants}</p>
            {e.tracked ? (
              <span className="text-[10px] bg-blue-100 text-blue-800 px-1 rounded">Tracciato</span>
            ) : (
              <Button size="sm" variant="outline" className="mt-1 h-6 text-xs">Crea scadenza</Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
