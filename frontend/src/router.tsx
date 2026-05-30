import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { DeadlinesPage } from "@/pages/DeadlinesPage";
import { AgentPage } from "@/pages/AgentPage";
import { ConfirmationsPage } from "@/pages/ConfirmationsPage";
import { EmailDraftsPage } from "@/pages/EmailDraftsPage";
import { AuditPage } from "@/pages/AuditPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { LoginPage } from "@/pages/LoginPage";

function AuthGuard() {
  const token = localStorage.getItem("acg_token");
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "documents", element: <DocumentsPage /> },
          { path: "documents/:id", element: <DocumentsPage /> },
          { path: "deadlines", element: <DeadlinesPage /> },
          { path: "agent", element: <AgentPage /> },
          { path: "confirmations", element: <ConfirmationsPage /> },
          { path: "email-drafts", element: <EmailDraftsPage /> },
          { path: "audit", element: <AuditPage /> },
          { path: "settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
]);
