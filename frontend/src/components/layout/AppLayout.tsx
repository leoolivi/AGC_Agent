import { NavLink, Outlet } from "react-router-dom";
import {
  Inbox,
  FileText,
  CalendarClock,
  MessageSquare,
  CheckCircle,
  Mail,
  Shield,
  Settings,
  Bell,
  LogOut,
} from "lucide-react";
import { useUnreadCount } from "@/api/hooks";
import { useAuthStore } from "@/store/auth";

const navItems = [
  { to: "/", icon: Inbox, label: "Dashboard" },
  { to: "/documents", icon: FileText, label: "Documenti" },
  { to: "/deadlines", icon: CalendarClock, label: "Scadenze" },
  { to: "/agent", icon: MessageSquare, label: "Chat Agent" },
  { to: "/confirmations", icon: CheckCircle, label: "Conferme" },
  { to: "/email-drafts", icon: Mail, label: "Email" },
  { to: "/audit", icon: Shield, label: "Audit Log" },
  { to: "/settings", icon: Settings, label: "Impostazioni" },
];

export function AppLayout() {
  const { data: unread } = useUnreadCount();
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
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
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
              end={to === "/"}
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t">
          <button
            onClick={() => { logout(); window.location.href = "/login"; }}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent w-full"
          >
            <LogOut className="h-4 w-4" />
            Esci
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 border-b flex items-center justify-end px-6">
          <div className="flex items-center gap-4">
            <button className="relative" aria-label="Notifiche">
              <Bell className="h-5 w-5 text-muted-foreground" />
              {unread && unread.unread_count > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-urgent text-[10px] text-white flex items-center justify-center">
                  {unread.unread_count}
                </span>
              )}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
