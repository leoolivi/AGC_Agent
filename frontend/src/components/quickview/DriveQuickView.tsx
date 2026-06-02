import { useState } from "react";
import { HardDrive } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DriveFile {
  id: string;
  name: string;
  folder: string;
  imported?: boolean;
}

const MOCK_FILES: DriveFile[] = [
  { id: "1", name: "Contratto_2026.pdf", folder: "Contratti" },
  { id: "2", name: "Fattura_Mar.pdf", folder: "Fatture", imported: true },
];

export function DriveQuickView() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");

  const files = MOCK_FILES.filter((f) => f.name.toLowerCase().includes(query.toLowerCase()));

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <HardDrive className="h-4 w-4" />
        <h3 className="font-medium text-sm">Drive — ultimi 30 giorni</h3>
      </div>
      <input
        className="w-full border rounded px-2 py-1 text-sm"
        placeholder="Cerca file..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <ul className="space-y-1 max-h-64 overflow-y-auto">
        {files.map((f) => (
          <li key={f.id} className="flex items-center gap-2 text-sm p-2 rounded hover:bg-accent">
            <input type="checkbox" checked={selected.has(f.id)} onChange={() => toggle(f.id)} disabled={f.imported} />
            <span className="flex-1 truncate">{f.name}</span>
            <span className="text-xs text-muted-foreground">{f.folder}</span>
            {f.imported && <span className="text-[10px] bg-green-100 text-green-800 px-1 rounded">Già importato</span>}
          </li>
        ))}
      </ul>
      {selected.size > 0 && (
        <Button size="sm" className="w-full">Importa {selected.size} file</Button>
      )}
    </div>
  );
}
