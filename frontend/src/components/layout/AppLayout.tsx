import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
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
import { useState, useEffect, useRef, useCallback } from "react";
import { AgentPage } from "@/pages/AgentPage";

const navItems = [
  { to: "/", icon: Inbox, label: "Inbox" },
  { to: "/agent", icon: Bot, label: "Agent" },
  { to: "/documents", icon: FileText, label: "Documenti" },
  { to: "/deadlines", icon: CalendarClock, label: "Scadenze" },
  /* { to: "/reports", icon: BarChart3, label: "Report" }, */
  /* { to: "/relations", icon: Network, label: "Relazioni" }, */
];

const settingsItems = [
  { to: "/settings", label: "Sorgenti e account" },
  /* { to: "/settings/escalation", label: "Regole Escalation" }, */
];

const PANEL_MIN_WIDTH = 280;
const PANEL_MAX_WIDTH = 900;
const PANEL_DEFAULT_WIDTH = 420;

export function AppLayout() {
  const { data: unread } = useUnreadCount();
  const { data: confirmations } = useConfirmations();
  const handleEvent = useRealtimeStore((s) => s.handleEvent);
  const { connectionState } = useWebSocket({
    onMessage: (data) =>
      handleEvent(data as { event_type: string; payload: Record<string, unknown> }),
  });
  const [agentOpen, setAgentOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(PANEL_DEFAULT_WIDTH);
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const badgeCount = (unread?.unread_count ?? 0) + (confirmations?.length ?? 0);
  const isAgentRoute = location.pathname === "/agent";

  useEffect(() => {
    if (isAgentRoute) setAgentOpen(false);
  }, [isAgentRoute]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const onDragStart = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = panelWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [panelWidth]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = e.clientX - dragStartX.current;
      const next = Math.min(PANEL_MAX_WIDTH, Math.max(PANEL_MIN_WIDTH, dragStartWidth.current + delta));
      setPanelWidth(next);
    };
    const onMouseUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-64 border-r bg-sidebar flex flex-col shrink-0">
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
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
              {to === "/" && badgeCount > 0 && (
                <span className="ml-auto text-[10px] bg-urgent text-white rounded-full px-1.5">
                  {badgeCount}
                </span>
              )}
            </NavLink>
          ))}
          <div className="pt-4 pb-1 px-3 text-xs text-muted-foreground uppercase">
            Impostazioni
          </div>
          {settingsItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                  isActive ? "bg-accent font-medium" : "text-muted-foreground hover:bg-accent"
                }`
              }
            >
              <Settings className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent w-full"
          >
            <LogOut className="h-4 w-4" /> Esci
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b flex items-center justify-between px-6 shrink-0">
          <ConnectionStatus state={connectionState} />
          {!isAgentRoute && (
            <div className="flex items-center gap-3">
              <AgentActivityIndicator />
              <button
                onClick={() => setAgentOpen((prev) => !prev)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm hover:bg-accent"
              >
                <MessageSquare className="h-4 w-4" /> Agent
              </button>
            </div>
          )}
        </header>

        <div className="flex flex-row flex-1 overflow-hidden">
          {agentOpen && !isAgentRoute && (
            <>
              <div
                className="flex-shrink-0 overflow-y-auto bg-muted/30 p-4"
                style={{ width: panelWidth }}
              >
                <AgentPage />
              </div>
              <div
                className="w-1 flex-shrink-0 cursor-col-resize bg-border hover:bg-primary/40 transition-colors active:bg-primary/60"
                onMouseDown={onDragStart}
              />
            </>
          )}

          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}