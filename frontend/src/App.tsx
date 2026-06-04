import { useEffect, useState, type FormEvent } from "react";

type Role = "admin" | "viewer";

interface Unit {
  number: string;
  ownership_pct: number;
}

interface Account {
  name: string;
}

interface Category {
  name: string;
}

interface Reference {
  units: Unit[];
  accounts: Account[];
  categories: Category[];
}

type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "authenticated"; role: Role };

async function fetchRole(): Promise<Role | null> {
  const res = await fetch("/api/auth/me", { credentials: "include" });
  if (!res.ok) return null;
  const data = await res.json();
  return (data.role as Role) ?? null;
}

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });

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

  return <DashboardShell role={auth.role} onLogout={refreshAuth} />;
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      onAuthenticated();
    } else if (res.status === 429) {
      setError("Too many attempts. Please wait and try again.");
    } else {
      setError("Incorrect password.");
    }
  }

  return (
    <main>
      <h1>DWCOA Financials</h1>
      <form onSubmit={handleSubmit} aria-label="Log in">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Log in</button>
        {error && <p role="alert">{error}</p>}
      </form>
    </main>
  );
}

function DashboardShell({ role, onLogout }: { role: Role; onLogout: () => void }) {
  const [reference, setReference] = useState<Reference | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch("/api/reference", { credentials: "include" });
      if (!res.ok) return;
      const data = (await res.json()) as Reference;
      if (active) setReference(data);
    })();
    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    onLogout();
  }

  return (
    <main>
      <header>
        <h1>DWCOA Financials</h1>
        {role === "admin" && (
          <div data-testid="admin-only">
            <button type="button">Manage</button>
          </div>
        )}
        <button type="button" onClick={handleLogout}>
          Log out
        </button>
      </header>

      <section aria-label="Units">
        <h2>Units</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Unit</th>
              <th scope="col">Ownership</th>
            </tr>
          </thead>
          <tbody>
            {reference?.units.map((unit) => (
              <tr key={unit.number}>
                <td>{unit.number}</td>
                <td>{(unit.ownership_pct * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
