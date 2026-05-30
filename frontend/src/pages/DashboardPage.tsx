import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useInbox, useUnreadCount, useActOnInbox, useDismissInbox } from "@/api/hooks";
import type { InboxItem } from "@/api/types";

type Urgency = InboxItem["urgency"];

const urgencyStyles: Record<Urgency, { border: string; badge: string; label: string }> = {
  immediate: { border: "border-l-4 border-l-urgent", badge: "bg-urgent text-white", label: "Urgente" },
  today: { border: "border-l-4 border-l-warning", badge: "bg-warning text-white", label: "Oggi" },
  this_week: { border: "border-l-4 border-l-muted-foreground", badge: "bg-muted text-foreground", label: "Settimana" },
  low: { border: "border-l-4 border-l-border", badge: "bg-muted text-muted-foreground", label: "Bassa" },
};

function InboxCard({ item }: { item: InboxItem }) {
  const style = urgencyStyles[item.urgency];
  const actMutation = useActOnInbox();
  const dismissMutation = useDismissInbox();

  return (
    <Card className={style.border}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Badge className={style.badge}>{style.label}</Badge>
          <span className="text-xs text-muted-foreground">{item.event_type}</span>
        </div>
        <p className="text-sm">{item.agent_analysis}</p>
        <div className="flex gap-2 flex-wrap">
          {item.suggested_actions
            .filter((a) => a.id !== "dismiss")
            .map((action) => (
              <Button
                key={action.id}
                size="sm"
                variant="outline"
                disabled={actMutation.isPending}
                onClick={() => actMutation.mutate({ itemId: item.id, actionId: action.id })}
              >
                {action.label}
              </Button>
            ))}
          <Button
            size="sm"
            variant="ghost"
            className="text-muted-foreground"
            disabled={dismissMutation.isPending}
            onClick={() => dismissMutation.mutate(item.id)}
          >
            Ignora
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data: items, isLoading, error } = useInbox("pending");
  const { data: unread } = useUnreadCount();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Inbox — main column */}
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Agent Inbox</h2>
          {unread && <Badge variant="secondary">{unread.unread_count} da leggere</Badge>}
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Caricamento...</p>}
        {error && <p className="text-sm text-destructive">Errore nel caricamento inbox</p>}
        {items && items.length === 0 && (
          <p className="text-sm text-muted-foreground">Nessun elemento in inbox.</p>
        )}
        {items?.map((item) => <InboxCard key={item.id} item={item} />)}
      </div>

      {/* Sidebar widgets */}
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Scadenze</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md bg-urgent/10 p-2">
                <div className="text-2xl font-bold text-urgent">—</div>
                <div className="text-xs text-muted-foreground">Scadute</div>
              </div>
              <div className="rounded-md bg-warning/10 p-2">
                <div className="text-2xl font-bold text-warning">—</div>
                <div className="text-xs text-muted-foreground">7 giorni</div>
              </div>
              <div className="rounded-md bg-success/10 p-2">
                <div className="text-2xl font-bold text-success">—</div>
                <div className="text-xs text-muted-foreground">30 giorni</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
