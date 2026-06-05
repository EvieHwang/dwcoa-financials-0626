import { useEffect, useMemo, useState, type FormEvent } from "react";

type Role = "admin" | "viewer";

interface Unit {
  number: string;
  ownership_pct: number;
}

interface Account {
  name: string;
  masked_number?: string;
}

interface Category {
  name: string;
}

interface Reference {
  units: Unit[];
  accounts: Account[];
  categories: Category[];
}

interface Transaction {
  id: number;
  account_number: string;
  account_name: string;
  post_date: string;
  check_number: string | null;
  description: string;
  debit: number | null;
  credit: number | null;
  status: string;
  balance: number;
  category: string | null;
}

interface TransactionsResponse {
  transactions: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

interface UploadSummary {
  added: number;
  skipped_duplicate: number;
  unknown_account_count: number;
  unknown_accounts: string[];
  total: number;
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

function centsToUsd(cents: number | null): string {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

function yearOptions(): number[] {
  // A deterministic recent range that always includes the migrated history's
  // years; not clock-fragile (clamped so the lower bound stays well below today).
  const startYear = Math.max(new Date().getFullYear(), 2026);
  return Array.from({ length: startYear - 2018 }, (_, i) => startYear - i);
}

function DashboardShell({ role, onLogout }: { role: Role; onLogout: () => void }) {
  const [reference, setReference] = useState<Reference | null>(null);

  // Transactions table state.
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [year, setYear] = useState("");
  const [account, setAccount] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  // Upload control state (admin only).
  const [file, setFile] = useState<File | null>(null);
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

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

  // Reload the table whenever a filter, the page, or the reload token changes.
  // `limit` is intentionally not a dependency: it is set from the response, and
  // re-reading the latest value inside the effect avoids a request loop.
  useEffect(() => {
    let active = true;
    void (async () => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));
      if (year) params.set("year", year);
      if (account) params.set("account", account);
      const res = await fetch(`/api/transactions?${params.toString()}`, {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) {
          setTxns([]);
          setTotal(0);
        }
        return;
      }
      const data = (await res.json()) as TransactionsResponse;
      if (active) {
        setTxns(data.transactions);
        setTotal(data.total);
        setLimit(data.limit);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, account, offset, reloadToken]);

  const accountOptions = useMemo(() => {
    const masked = new Map<string, string | undefined>();
    reference?.accounts.forEach((a) => masked.set(a.name, a.masked_number));
    txns.forEach((t) => {
      if (!masked.has(t.account_name)) masked.set(t.account_name, t.account_number);
    });
    return Array.from(masked.entries()).map(([name, number]) => ({ name, number }));
  }, [reference, txns]);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    onLogout();
  }

  async function handleUpload() {
    if (!file) return;
    setUploadError(null);
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/transactions/upload", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      setUploadSummary(null);
      let message = "Upload failed.";
      try {
        const data = await res.json();
        if (typeof data?.detail === "string") message = data.detail;
        else if (data?.detail?.errors) message = data.detail.errors.join(" ");
      } catch {
        /* keep the generic message */
      }
      setUploadError(message);
      return;
    }
    const summary = (await res.json()) as UploadSummary;
    setUploadSummary(summary);
    // Reflect the new rows in the table.
    setOffset(0);
    setReloadToken((t) => t + 1);
  }

  const hasNextPage = offset + limit < total;
  const hasPrevPage = offset > 0;

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

      {role === "admin" && (
        <section>
          <h2>Upload transactions</h2>
          <label htmlFor="csv-upload">Upload transactions CSV</label>
          <input
            id="csv-upload"
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <button type="button" onClick={handleUpload}>
            Upload
          </button>
          {uploadError && <p role="alert">{uploadError}</p>}
          {uploadSummary && (
            <div data-testid="upload-summary" role="status" aria-live="polite">
              Added {uploadSummary.added}, skipped {uploadSummary.skipped_duplicate}{" "}
              duplicate{uploadSummary.skipped_duplicate === 1 ? "" : "s"},{" "}
              {uploadSummary.unknown_account_count} unknown account
              {uploadSummary.unknown_account_count === 1 ? "" : "s"} (
              {uploadSummary.total} rows read).
              {uploadSummary.unknown_accounts.length > 0 && (
                <> Unknown: {uploadSummary.unknown_accounts.join(", ")}.</>
              )}
            </div>
          )}
        </section>
      )}

      <section>
        <h2>Transactions</h2>
        <div>
          <label htmlFor="filter-year">Year</label>
          <select
            id="filter-year"
            value={year}
            onChange={(e) => {
              setOffset(0);
              setYear(e.target.value);
            }}
          >
            <option value="">All years</option>
            {yearOptions().map((y) => (
              <option key={y} value={String(y)}>
                {y}
              </option>
            ))}
          </select>

          <label htmlFor="filter-account">Account</label>
          <select
            id="filter-account"
            value={account}
            onChange={(e) => {
              setOffset(0);
              setAccount(e.target.value);
            }}
          >
            <option value="">All accounts</option>
            {accountOptions.map((a) => (
              <option key={a.name} value={a.name}>
                {a.number ? `${a.name} (${a.number})` : a.name}
              </option>
            ))}
          </select>
        </div>

        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Account</th>
              <th scope="col">Check</th>
              <th scope="col">Description</th>
              <th scope="col">Debit</th>
              <th scope="col">Credit</th>
              <th scope="col">Balance</th>
              <th scope="col">Status</th>
              <th scope="col">Category</th>
            </tr>
          </thead>
          <tbody>
            {txns.map((t) => (
              <tr key={t.id}>
                <td>{t.post_date}</td>
                <td>{t.account_name}</td>
                <td>{t.check_number ?? ""}</td>
                <td>{t.description}</td>
                <td>{centsToUsd(t.debit)}</td>
                <td>{centsToUsd(t.credit)}</td>
                <td>{centsToUsd(t.balance)}</td>
                <td>{t.status}</td>
                <td>{t.category ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div>
          <span>
            {total === 0
              ? "No transactions"
              : `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
          </span>
          <button
            type="button"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={!hasPrevPage}
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setOffset(offset + limit)}
            disabled={!hasNextPage}
          >
            Next
          </button>
        </div>
      </section>
    </main>
  );
}
