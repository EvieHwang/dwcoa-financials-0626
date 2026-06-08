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

/** Normalized record of every fetch call: path, method, and parsed JSON body. */
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

// --- App-mount fixtures (App fetches these on load) ------------------------

export const REFERENCE = {
  units: [{ number: "101", ownership_pct: 0.117 }],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
    { name: "Reserve Fund", masked_number: "****9226" },
  ],
  categories: [{ name: "Insurance Premiums", type: "Expense" }],
};

export const TRANSACTIONS = { transactions: [], total: 0, limit: 50, offset: 0 };

export const BUDGETS = { year: 2030, locked: false, locked_at: null, budgets: [] };

// --- the dashboard payload under test (all money integer cents) ------------
// Distinctive values so USD assertions are unambiguous.
export const DASHBOARD = {
  as_of_date: "2030-06-30",
  year: 2030,
  accounts: [
    { name: "Checking", balance: 250000, beginning_balance: 100000 },
    { name: "Savings", balance: 150000, beginning_balance: 150000 },
    { name: "Reserve Fund", balance: 500000, beginning_balance: 450000 },
  ],
  total_cash: 900000, // $9,000.00
  income_summary: {
    annual_budget: 120000,
    prorated_budget: 60000,
    actual: 33300, // $333.00 — distinctive
    remaining: 26700,
    categories: [
      {
        category_id: 1,
        name: "Dues 101",
        annual_budget: 120000,
        prorated_budget: 60000,
        actual: 33300,
        remaining: 26700,
      },
    ],
  },
  expense_summary: {
    annual_budget: 120000,
    prorated_budget: 60000,
    actual: 50000,
    remaining: 10000,
    categories: [
      {
        category_id: 11,
        name: "Insurance Premiums",
        annual_budget: 120000,
        prorated_budget: 60000,
        actual: 50000, // $500.00
        remaining: 10000, // $100.00
      },
    ],
  },
  reserve_fund: {
    budget: 600000,
    contributions: 300000,
    expenses: 40000,
    net: 260000, // $2,600.00 — distinctive
    beginning_balance: 4500000,
  },
  monthly_cashflow: [
    { month: 1, income: 0, expenses: 0 },
    { month: 2, income: 33300, expenses: 12000 },
    { month: 3, income: 0, expenses: 0 },
    { month: 4, income: 0, expenses: 0 },
    { month: 5, income: 0, expenses: 8000 },
    { month: 6, income: 0, expenses: 0 },
  ],
};
