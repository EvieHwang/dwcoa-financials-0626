import { useEffect, useState } from "react";
import type { AuthState, Role } from "@/lib/types";
import { useTheme } from "@/lib/useTheme";
import Login from "@/screens/Login";
import AppShell from "@/shell/AppShell";

// Top-level orchestrator: owns the auth state machine and the single source of
// truth for theme (applied to <html>), then renders either the branded login or
// the authenticated app shell. Role is read only from /api/auth/me and flows into
// the shell; there is no client-settable role anywhere (visual-redesign-009).
async function fetchRole(): Promise<Role | null> {
  const res = await fetch("/api/auth/me", { credentials: "include" });
  if (!res.ok) return null;
  const data = await res.json();
  return (data.role as Role) ?? null;
}

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });
  const { isDark, toggle } = useTheme();

  async function refreshAuth() {
    const role = await fetchRole();
    setAuth(role ? { status: "authenticated", role } : { status: "unauthenticated" });
  }

  useEffect(() => {
    void refreshAuth();
  }, []);

  if (auth.status === "loading") {
    return <main aria-busy="true" />;
  }

  if (auth.status === "unauthenticated") {
    return <Login onAuthenticated={refreshAuth} />;
  }

  return (
    <AppShell
      role={auth.role}
      onLogout={refreshAuth}
      isDark={isDark}
      onToggleTheme={toggle}
    />
  );
}
