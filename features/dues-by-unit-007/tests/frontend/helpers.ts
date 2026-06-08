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

export const REFERENCE = {
  units: [
    { number: "101", ownership_pct: 0.117 },
    { number: "102", ownership_pct: 0.104 },
  ],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
    { name: "Reserve Fund", masked_number: "****9226" },
  ],
  categories: [{ name: "Insurance Premiums", type: "Expense" }],
};

export const TRANSACTIONS = { transactions: [], total: 0, limit: 50, offset: 0 };
export const BUDGETS = { year: 2030, locked: false, locked_at: null, budgets: [] };

// The dashboard payload the embedding view also needs (distinct USD values so dues
// assertions never collide with dashboard ones: dashboard total cash is $9,000.00).
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

// --- the dues payload under test (all money integer cents) -----------------
// Distinctive values so USD assertions are unambiguous (outstanding $4,540.30).
export const DUES = {
  as_of_date: "2026-06-30",
  year: 2026,
  dues_tracked: true,
  operating_budget: 5590000,
  units: [
    {
      unit: "101",
      ownership_per_mille: 117,
      carryover: 0,
      annual_dues: 654030,
      expected_total: 654030,
      paid: 200000,
      outstanding: 454030, // $4,540.30 — distinctive
    },
    {
      unit: "102",
      ownership_per_mille: 104,
      carryover: 50000,
      annual_dues: 581360,
      expected_total: 631360,
      paid: 0,
      outstanding: 631360,
    },
  ],
  totals: {
    carryover: 50000,
    annual_dues: 1235390,
    expected_total: 1285390,
    paid: 200000,
    outstanding: 1085390,
  },
};

// The pre-2025 "not tracked" payload.
export const DUES_NOT_TRACKED = {
  as_of_date: "2024-06-30",
  year: 2024,
  dues_tracked: false,
  operating_budget: 0,
  units: [],
  totals: { carryover: 0, annual_dues: 0, expected_total: 0, paid: 0, outstanding: 0 },
};
