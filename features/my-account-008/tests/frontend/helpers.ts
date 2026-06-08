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
 * methods were requested. Any unlisted route resolves 404 so missing wiring
 * fails loudly.
 */
export function stubFetch(routes: Routes) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
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
    return { url, path, method: (init.method ?? "GET").toUpperCase(), body: undefined };
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

// --- App-mount fixtures (App fetches these on load) ------------------------

// All nine seeded units, so a unit selector sourced from /api/reference has them.
export const REFERENCE = {
  units: [
    { number: "101", ownership_pct: 0.117 },
    { number: "102", ownership_pct: 0.104 },
    { number: "103", ownership_pct: 0.112 },
    { number: "201", ownership_pct: 0.117 },
    { number: "202", ownership_pct: 0.104 },
    { number: "203", ownership_pct: 0.112 },
    { number: "301", ownership_pct: 0.117 },
    { number: "302", ownership_pct: 0.104 },
    { number: "303", ownership_pct: 0.112 },
  ],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
  ],
  categories: [{ name: "Insurance Premiums", type: "Expense" }],
};

export const TRANSACTIONS = { transactions: [], total: 0, limit: 50, offset: 0 };
export const BUDGETS = { year: 2030, locked: false, locked_at: null, budgets: [] };

// The dashboard + dues payloads the embedding view also fetches. Distinct USD
// values so My Account assertions never collide (dashboard total cash $9,000.00;
// dues outstanding $4,540.30 — neither equals the account sentinel below).
export const DASHBOARD = {
  as_of_date: "2026-06-30",
  year: 2026,
  accounts: [{ name: "Checking", balance: 900000, beginning_balance: 0 }],
  total_cash: 900000,
  income_summary: { annual_budget: 0, prorated_budget: 0, actual: 0, remaining: 0, categories: [] },
  expense_summary: { annual_budget: 0, prorated_budget: 0, actual: 0, remaining: 0, categories: [] },
  reserve_fund: { budget: 0, contributions: 0, expenses: 0, net: 0, beginning_balance: 0 },
  monthly_cashflow: [{ month: 1, income: 0, expenses: 0 }],
};

export const DUES = {
  as_of_date: "2026-06-30",
  year: 2026,
  dues_tracked: true,
  operating_budget: 5590000,
  units: [
    { unit: "101", ownership_per_mille: 117, carryover: 0, annual_dues: 654030,
      expected_total: 654030, paid: 200000, outstanding: 454030 },
  ],
  totals: { carryover: 0, annual_dues: 654030, expected_total: 654030,
            paid: 200000, outstanding: 454030 },
};

// --- the account (My Account) payload under test — all money integer cents --
// Sentinel value: remaining_balance 2,110,000 = $21,100.00 (unique across fixtures)
// proves the statement loaded for the selected unit.
export const ACCOUNT = {
  unit: "101",
  ownership_per_mille: 117,
  as_of_date: "2026-06-30",
  year: 2026,
  dues_tracked: true,
  current_year: {
    year: 2026,
    carryover: 770000,
    annual_dues: 2340000,
    total_due: 3110000,
    paid_ytd: 1000000,
    remaining_balance: 2110000, // $21,100.00 — distinctive sentinel
  },
  prior_year: {
    year: 2025,
    data_available: true,
    annual_dues_budgeted: 1170000,
    total_paid: 500000,
    balance_carried_forward: 770000,
  },
  payment_guidance: {
    standard_monthly: 195000, // $1,950.00
    months_remaining: 6,
    suggested_monthly: 351667, // $3,516.67
    status: "owes",
  },
  recent_payments: [{ date: "2026-05-01", amount: 1000000 }], // $10,000.00
};

// The pre-2025 "not tracked" payload.
export const ACCOUNT_NOT_TRACKED = {
  unit: "101",
  ownership_per_mille: 117,
  as_of_date: "2024-06-30",
  year: 2024,
  dues_tracked: false,
  current_year: null,
  prior_year: null,
  payment_guidance: null,
  recent_payments: [],
};
