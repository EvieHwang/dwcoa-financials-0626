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

export const REFERENCE = {
  units: [{ number: "101", ownership_pct: 0.117 }],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
  ],
  categories: [{ name: "Insurance Premiums", type: "Expense" }],
};

// Empty transactions so the dashboard's table fetch resolves cleanly.
export const TRANSACTIONS = { transactions: [], total: 0, limit: 50, offset: 0 };

// A two-line budget for 2025: one with an inherited timing, one overridden.
export const BUDGETS = {
  year: 2025,
  locked: false,
  locked_at: null,
  budgets: [
    {
      category_id: 11,
      category_name: "Insurance Premiums",
      category_type: "Expense",
      annual_amount: 450000, // $4,500.00
      timing: null,
      category_default_timing: "monthly",
      effective_timing: "monthly",
    },
    {
      category_id: 12,
      category_name: "Seattle City Light",
      category_type: "Expense",
      annual_amount: 600000, // $6,000.00
      timing: "quarterly",
      category_default_timing: "monthly",
      effective_timing: "quarterly",
    },
  ],
};
