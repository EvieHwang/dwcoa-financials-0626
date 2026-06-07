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
  id?: number;
  name: string;
}

interface Reference {
  units: Unit[];
  accounts: Account[];
  categories: Category[];
}

interface Rule {
  id: number;
  pattern: string;
  category_id: number;
  category: string | null;
  account: string | null;
  amount_min: number | null;
  amount_max: number | null;
  priority: number;
  confidence: number;
  active: number | boolean;
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
  needs_review?: number | boolean;
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

interface BudgetLine {
  category_id: number;
  category_name: string;
  category_type: string;
  annual_amount: number;
  timing: string | null;
  category_default_timing: string;
  effective_timing: string;
}

interface BudgetResponse {
  year: number;
  locked: boolean;
  locked_at: string | null;
  budgets: BudgetLine[];
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

// The budget editor (R8): reads a year's budget (R1), and for an admin issues
// upsert (R2, integer cents at the boundary), copy-year (R3, confirming then
// retrying with overwrite on a 409), and lock/unlock (R4). A viewer sees the
// budget read-only — no save / copy / lock controls. A locked year disables the
// amount inputs. The proration engine (R7) is backend-only this slice, so the
// editor shows planned annual amounts, not prorated YTD.
function BudgetEditor({ role }: { role: Role }) {
  const isAdmin = role === "admin";
  const [budgetYear] = useState(() =>
    String(Math.max(new Date().getFullYear(), 2025)),
  );
  const [data, setData] = useState<BudgetResponse | null>(null);
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [reload, setReload] = useState(0);
  const [copyConflict, setCopyConflict] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch(`/api/budgets?year=${budgetYear}`, {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) setData(null);
        return;
      }
      const body = (await res.json()) as BudgetResponse;
      if (active) {
        setData(body);
        setEdits({});
      }
    })();
    return () => {
      active = false;
    };
  }, [budgetYear, reload]);

  if (!data) return null;
  const locked = data.locked;

  function dollarsValue(line: BudgetLine): string {
    const edited = edits[line.category_id];
    if (edited !== undefined) return edited;
    return String(line.annual_amount / 100);
  }

  async function handleSave() {
    if (!data) return;
    for (const line of data.budgets) {
      const edited = edits[line.category_id];
      if (edited === undefined) continue;
      // Dollars are converted to integer cents at the API boundary.
      const cents = Math.round(Number(edited) * 100);
      await fetch("/api/budgets", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          year: data.year,
          category_id: line.category_id,
          annual_amount: cents,
        }),
      });
    }
    setReload((t) => t + 1);
  }

  async function postCopy(overwrite: boolean) {
    if (!data) return null;
    return fetch("/api/budgets/copy", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        from_year: data.year - 1,
        to_year: data.year,
        ...(overwrite ? { overwrite: true } : {}),
      }),
    });
  }

  async function handleCopy() {
    const res = await postCopy(false);
    if (!res) return;
    if (res.status === 409) {
      // Target non-empty: surface a confirmation and retry with overwrite.
      setCopyConflict(true);
      return;
    }
    setCopyConflict(false);
    if (res.ok) setReload((t) => t + 1);
  }

  async function handleCopyConfirm() {
    await postCopy(true);
    setCopyConflict(false);
    setReload((t) => t + 1);
  }

  async function handleLock() {
    if (!data) return;
    await fetch("/api/budgets/lock", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ year: data.year, locked: !data.locked }),
    });
    setReload((t) => t + 1);
  }

  return (
    <section aria-label="Budget">
      <h2>Budget {data.year}</h2>
      {isAdmin && (
        <div>
          <button type="button" onClick={handleSave} disabled={locked}>
            Save
          </button>
          <button type="button" onClick={handleCopy} disabled={locked}>
            Copy year
          </button>
          <button type="button" onClick={handleLock}>
            {locked ? "Unlock year" : "Lock year"}
          </button>
          {copyConflict && (
            <button type="button" onClick={handleCopyConfirm}>
              Overwrite
            </button>
          )}
          {locked && <span role="status">Year locked</span>}
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th scope="col">Category</th>
            <th scope="col">Annual budget</th>
            <th scope="col">Timing</th>
            {isAdmin && <th scope="col">Edit (USD)</th>}
          </tr>
        </thead>
        <tbody>
          {data.budgets.map((line) => (
            <tr key={line.category_id}>
              <td>{line.category_name}</td>
              <td>{centsToUsd(line.annual_amount)}</td>
              <td>{line.effective_timing}</td>
              {isAdmin && (
                <td>
                  <input
                    type="number"
                    step="0.01"
                    aria-label={`${line.category_name} amount`}
                    value={dollarsValue(line)}
                    disabled={locked}
                    onChange={(e) =>
                      setEdits((prev) => ({
                        ...prev,
                        [line.category_id]: e.target.value,
                      }))
                    }
                  />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
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

  // Categorization state (admin only): the review queue, the rules list, the
  // single create-rule form (also driven by "Create rule" in the review queue),
  // and a reload token bumped after every mutation so the queue/table/rules
  // reflect the sweep.
  const [reviewTxns, setReviewTxns] = useState<Transaction[]>([]);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [rules, setRules] = useState<Rule[]>([]);
  const [reviewCat, setReviewCat] = useState<Record<number, string>>({});
  const [ruleForm, setRuleForm] = useState({ pattern: "", category_id: "" });
  const [composingReviewId, setComposingReviewId] = useState<number | null>(null);
  const [adminReload, setAdminReload] = useState(0);
  const [adminDataLoaded, setAdminDataLoaded] = useState(false);

  const categories = reference?.categories ?? [];
  const firstCatId = categories[0]?.id;
  const defaultCatValue = firstCatId !== undefined ? String(firstCatId) : "";

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

  // Load the review queue and the rules list (admin only), refreshed whenever a
  // mutation bumps the reload token.
  useEffect(() => {
    if (role !== "admin") return;
    let active = true;
    void (async () => {
      const [queueRes, rulesRes] = await Promise.all([
        fetch("/api/transactions?needs_review=true", { credentials: "include" }),
        fetch("/api/rules", { credentials: "include" }),
      ]);
      if (active) {
        if (queueRes.ok) {
          const data = (await queueRes.json()) as TransactionsResponse;
          setReviewTxns(data.transactions ?? []);
          setReviewTotal(data.total ?? 0);
        } else {
          setReviewTxns([]);
          setReviewTotal(0);
        }
      }
      if (active) {
        if (rulesRes.ok) {
          const data = (await rulesRes.json()) as { rules: Rule[] };
          setRules(data.rules ?? []);
        } else {
          setRules([]);
        }
      }
      if (active) setAdminDataLoaded(true);
    })();
    return () => {
      active = false;
    };
  }, [role, adminReload]);

  function refreshAfterMutation() {
    setAdminReload((t) => t + 1);
    setReloadToken((t) => t + 1);
  }

  async function handleSaveFix(txn: Transaction) {
    const catId = Number(reviewCat[txn.id] ?? defaultCatValue);
    await fetch(`/api/transactions/${txn.id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ category_id: catId }),
    });
    refreshAfterMutation();
  }

  async function handleCreateRuleFromReview(txn: Transaction) {
    let pattern = txn.description;
    const res = await fetch(
      `/api/rules/suggest?description=${encodeURIComponent(txn.description)}`,
      { credentials: "include" },
    );
    if (res.ok) {
      const data = (await res.json()) as { pattern?: string };
      pattern = data.pattern ?? txn.description;
    }
    setComposingReviewId(txn.id);
    setRuleForm({
      pattern,
      category_id: reviewCat[txn.id] ?? defaultCatValue,
    });
  }

  async function handleCreateRule() {
    const catId = Number(ruleForm.category_id || defaultCatValue);
    await fetch("/api/rules", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pattern: ruleForm.pattern, category_id: catId }),
    });
    setRuleForm({ pattern: "", category_id: "" });
    setComposingReviewId(null);
    refreshAfterMutation();
  }

  async function handleDeleteRule(ruleId: number) {
    await fetch(`/api/rules/${ruleId}`, {
      method: "DELETE",
      credentials: "include",
    });
    refreshAfterMutation();
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

      {role === "admin" && adminDataLoaded && (
        <section data-testid="review-queue" aria-label="Review queue">
          <h2>
            Review queue{" "}
            <span data-testid="review-count" aria-label={`${reviewTotal} transactions need review`}>
              {reviewTotal}
            </span>
          </h2>
          <table>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Description</th>
                <th scope="col">Amount</th>
                <th scope="col">Category</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reviewTxns.map((t) => (
                <tr key={t.id}>
                  <td>{t.post_date}</td>
                  <td>{t.description}</td>
                  <td>{centsToUsd(t.debit ?? t.credit)}</td>
                  <td>
                    <select
                      aria-label="Category"
                      value={reviewCat[t.id] ?? defaultCatValue}
                      onChange={(e) =>
                        setReviewCat((prev) => ({ ...prev, [t.id]: e.target.value }))
                      }
                    >
                      {categories.map((c) => (
                        <option key={c.id ?? c.name} value={String(c.id ?? "")}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <button type="button" onClick={() => handleSaveFix(t)}>
                      Save
                    </button>
                    {composingReviewId === null && (
                      <button
                        type="button"
                        onClick={() => handleCreateRuleFromReview(t)}
                      >
                        Create rule
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {role === "admin" && adminDataLoaded && (
        <section data-testid="rules-editor" aria-label="Rules editor">
          <h2>Categorization rules</h2>

          <div>
            <label htmlFor="rule-pattern">Pattern</label>
            <input
              id="rule-pattern"
              type="text"
              value={ruleForm.pattern}
              onChange={(e) =>
                setRuleForm((prev) => ({ ...prev, pattern: e.target.value }))
              }
            />
            <label htmlFor="rule-category">Category</label>
            <select
              id="rule-category"
              value={ruleForm.category_id || defaultCatValue}
              onChange={(e) =>
                setRuleForm((prev) => ({ ...prev, category_id: e.target.value }))
              }
            >
              {categories.map((c) => (
                <option key={c.id ?? c.name} value={String(c.id ?? "")}>
                  {c.name}
                </option>
              ))}
            </select>
            <button type="button" onClick={handleCreateRule}>
              Create rule
            </button>
          </div>

          <table>
            <thead>
              <tr>
                <th scope="col">Pattern</th>
                <th scope="col">Category</th>
                <th scope="col">Conditions</th>
                <th scope="col">Priority</th>
                <th scope="col">Active</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.pattern}</td>
                  <td>{r.category}</td>
                  <td>
                    {[
                      r.account ? `acct=${r.account}` : null,
                      r.amount_min !== null ? `min=${r.amount_min}` : null,
                      r.amount_max !== null ? `max=${r.amount_max}` : null,
                    ]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </td>
                  <td>{r.priority}</td>
                  <td>{r.active ? "Yes" : "No"}</td>
                  <td>
                    <button type="button" onClick={() => handleDeleteRule(r.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <BudgetEditor role={role} />

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
