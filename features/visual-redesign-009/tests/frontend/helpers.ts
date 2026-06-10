import { vi } from "vitest";

type Routes = Record<string, { status?: number; body?: unknown }>;

interface SeenCall {
  url: string;
  path: string;
  method: string;
  body: unknown;
}

/**
 * Stub global fetch, routing by the pathname of the request URL (query string
 * ignored for matching). Returns the mock so tests can assert which URLs and
 * methods/bodies were requested. Any unlisted route resolves 404 so missing
 * wiring fails loudly.
 */
export function stubFetch(routes: Routes) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const path = new URL(url, "https://testserver").pathname;
    const match = routes[path];
    const status = match?.status ?? (match ? 200 : 404);
    const body = match?.body ?? {};
    return new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export function calls(fn: ReturnType<typeof stubFetch>): SeenCall[] {
  return fn.mock.calls.map((c) => {
    const input = c[0] as RequestInfo | URL;
    const init = (c[1] ?? {}) as RequestInit;
    const url = typeof input === "string" ? input : input.toString();
    const path = new URL(url, "https://testserver").pathname;
    let body: unknown = undefined;
    if (typeof init.body === "string") {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    return { url, path, method: (init.method ?? "GET").toUpperCase(), body };
  });
}

/** Calls to a given pathname, optionally filtered by HTTP method. */
export function callsTo(
  fn: ReturnType<typeof stubFetch>,
  path: string,
  method?: string,
): SeenCall[] {
  return calls(fn).filter(
    (c) => c.path === path && (method ? c.method === method.toUpperCase() : true),
  );
}

// --- Fixtures (all money integer cents) ------------------------------------

export const REFERENCE = {
  units: [
    { number: "101", ownership_pct: 0.117 },
    { number: "201", ownership_pct: 0.117 },
    { number: "303", ownership_pct: 0.104 },
  ],
  accounts: [
    { name: "Checking", masked_number: "****9242" },
    { name: "Savings", masked_number: "****7145" },
    { name: "Reserve Fund", masked_number: "****9226" },
  ],
  categories: [
    { id: 1, name: "Dues 101", type: "Income" },
    { id: 11, name: "Insurance Premiums", type: "Expense" },
  ],
};

export const DASHBOARD = {
  as_of_date: "2030-06-30",
  year: 2030,
  accounts: [
    { name: "Checking", balance: 250000, beginning_balance: 100000 },
    { name: "Savings", balance: 150000, beginning_balance: 150000 },
    { name: "Reserve Fund", balance: 500000, beginning_balance: 450000 },
  ],
  total_cash: 900000,
  income_summary: {
    annual_budget: 120000,
    prorated_budget: 60000,
    actual: 33300,
    remaining: 26700,
    categories: [
      { category_id: 1, name: "Dues 101", annual_budget: 120000, prorated_budget: 60000, actual: 33300, remaining: 26700 },
    ],
  },
  expense_summary: {
    annual_budget: 120000,
    prorated_budget: 60000,
    actual: 50000,
    remaining: 10000,
    categories: [
      { category_id: 11, name: "Insurance Premiums", annual_budget: 120000, prorated_budget: 60000, actual: 50000, remaining: 10000 },
    ],
  },
  reserve_fund: { budget: 600000, contributions: 300000, expenses: 40000, net: 260000, beginning_balance: 4500000 },
  monthly_cashflow: [
    { month: 1, income: 0, expenses: 0 },
    { month: 2, income: 33300, expenses: 12000 },
  ],
};

export const DUES = {
  as_of_date: "2030-06-30",
  year: 2030,
  dues_tracked: true,
  operating_budget: 1200000,
  units: [
    { unit: "101", ownership_per_mille: 117, carryover: 0, annual_dues: 140400, expected_total: 70200, paid: 70200, outstanding: 0 },
  ],
  totals: { carryover: 0, annual_dues: 140400, expected_total: 70200, paid: 70200, outstanding: 0 },
};

export const ACCOUNT = {
  unit: "101",
  ownership_per_mille: 117,
  as_of_date: "2030-06-30",
  year: 2030,
  dues_tracked: true,
  current_year: { year: 2030, carryover: 0, annual_dues: 140400, total_due: 140400, paid_ytd: 70200, remaining_balance: 70200 },
  prior_year: { year: 2029, data_available: true, annual_dues_budgeted: 140000, total_paid: 140000, balance_carried_forward: 0 },
  payment_guidance: { standard_monthly: 11700, months_remaining: 6, suggested_monthly: 11700, status: "owes" },
  recent_payments: [{ date: "2030-06-01", amount: 11700 }],
};

export const BUDGETS = {
  year: 2030,
  locked: false,
  locked_at: null,
  budgets: [
    { category_id: 11, category_name: "Insurance Premiums", category_type: "Expense", annual_amount: 120000, timing: null, category_default_timing: "monthly", effective_timing: "monthly" },
  ],
};

export const TRANSACTIONS = { transactions: [], total: 0, limit: 50, offset: 0 };
export const RULES = { rules: [] };

/** Every endpoint App may fetch, with safe bodies so any screen mounts cleanly. */
export function routes(role: "admin" | "viewer", extra: Routes = {}): Routes {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/dashboard": { body: DASHBOARD },
    "/api/dues": { body: DUES },
    "/api/account": { body: ACCOUNT },
    "/api/budgets": { body: BUDGETS },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/rules": { body: RULES },
    ...extra,
  };
}

// --- Theme test environment controls ---------------------------------------

/**
 * Control `window.matchMedia`. Pass a boolean to simulate a
 * `prefers-color-scheme: dark` result; pass `null` to remove matchMedia entirely
 * (older/headless environments). Restores nothing — call in beforeEach per test.
 */
export function setPrefersDark(prefersDark: boolean | null) {
  if (prefersDark === null) {
    // Simulate an environment with no matchMedia at all.
    // @ts-expect-error intentional deletion for the no-matchMedia path
    delete window.matchMedia;
    return;
  }
  const mql = (query: string): MediaQueryList =>
    ({
      matches: /dark/.test(query) ? prefersDark : false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
  vi.stubGlobal("matchMedia", vi.fn(mql));
}

/** True if the document root indicates dark theme (class or data-attribute). */
export function rootIsDark(): boolean {
  const el = document.documentElement;
  return el.classList.contains("dark") || el.getAttribute("data-theme") === "dark";
}

/** Reset the document root + persisted theme between tests. */
export function resetThemeState() {
  document.documentElement.classList.remove("dark");
  document.documentElement.removeAttribute("data-theme");
  localStorage.clear();
}
