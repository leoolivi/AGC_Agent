import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Inbox,
  FileText,
  CalendarClock,
  BarChart3,
  Network,
  Bot,
  Settings,
  LogOut,
  MessageSquare,
} from "lucide-react";
import { useUnreadCount, useConfirmations } from "@/api/hooks";
import { useAuthStore } from "@/store/auth";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useRealtimeStore } from "@/store/realtime";
import { ConnectionStatus } from "@/components/realtime/ConnectionStatus";
import { AgentActivityIndicator } from "@/components/realtime/AgentActivityIndicator";
import { useState } from "react";
import { AgentPage } from "@/pages/AgentPage";

const navItems = [
  { to: "/", icon: Inbox, label: "Inbox" },
  { to: "/agent", icon: Bot, label: "Agent" },
  { to: "/documents", icon: FileText, label: "Documenti" },
  { to: "/deadlines", icon: CalendarClock, label: "Scadenze" },
  { to: "/reports", icon: BarChart3, label: "Report" },
  { to: "/relations", icon: Network, label: "Relazioni" },
];

const settingsItems = [
  { to: "/settings", label: "Sorgenti e account" },
  { to: "/settings/escalation", label: "Regole Escalation" },
];

export function AppLayout() {
  const { data: unread } = useUnreadCount();
  const { data: confirmations } = useConfirmations();
  const handleEvent = useRealtimeStore((s) => s.handleEvent);
  const { connectionState } = useWebSocket({ onMessage: handleEvent });
  const [agentOpen, setAgentOpen] = useState(false);
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);

  const badgeCount = (unread?.unread_count ?? 0) + (confirmations?.length ?? 0);

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r bg-sidebar flex flex-col">
        <div className="p-4 border-b">
          <h1 className="text-lg font-bold">ACG</h1>
          <p className="text-xs text-muted-foreground">Admin & Compliance Guardian</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground hover:bg-accent"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
              {to === "/" && badgeCount > 0 && (
                <span className="ml-auto text-[10px] bg-urgent text-white rounded-full px-1.5">{badgeCount}</span>
              )}
            </NavLink>
          ))}
          <div className="pt-4 pb-1 px-3 text-xs text-muted-foreground uppercase">Impostazioni</div>
          {settingsItems.map(({ to, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${isActive ? "bg-accent font-medium" : "text-muted-foreground hover:bg-accent"}`
            }>
              <Settings className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t">
          <button onClick={() => { logout(); window.location.href = "/login"; }}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent w-full">
            <LogOut className="h-4 w-4" /> Esci
          </button>
        </div>
      </aside>

      {location.pathname !== "/agent" ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-14 border-b flex items-center justify-between px-6">
            <ConnectionStatus state={connectionState} />
            <div className="flex items-center gap-3">
              <AgentActivityIndicator />
              <button
                onClick={() => setAgentOpen(!agentOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm hover:bg-accent"
              >
                <MessageSquare className="h-4 w-4" /> Agent
              </button>
            </div>
          </header>

          {agentOpen && (
            <div className="border-b p-4 bg-muted/30 max-h-64 overflow-auto">
              <AgentPage></AgentPage>
            </div>
          )}

          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-14 border-b flex items-center justify-between px-6">
            <ConnectionStatus state={connectionState} />
          </header>

          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      )}
    </div>
  );
}
