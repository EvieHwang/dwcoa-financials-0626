import { vi } from "vitest";

type Routes = Record<string, { status?: number; body?: unknown }>;

/**
 * Stub global fetch, routing by the pathname of the request URL (query string
 * ignored for matching). Returns the mock so tests can assert which URLs (with
 * query params and methods) were requested. Any unlisted route resolves 404 so
 * missing wiring fails loudly.
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

export function calledUrls(fn: ReturnType<typeof stubFetch>): string[] {
  return fn.mock.calls.map((c) => {
    const input = c[0] as RequestInfo | URL;
    return typeof input === "string" ? input : input.toString();
  });
}

/** The fetch call (url + init) whose pathname matches `path`, with optional method. */
export function callTo(
  fn: ReturnType<typeof stubFetch>,
  path: string,
  method?: string,
) {
  return fn.mock.calls.find((c) => {
    const url = typeof c[0] === "string" ? c[0] : String(c[0]);
    const p = new URL(url, "https://testserver").pathname;
    if (p !== path) return false;
    if (!method) return true;
    const m = (c[1] as RequestInit | undefined)?.method ?? "GET";
    return m.toUpperCase() === method.toUpperCase();
  });
}

export function bodyOf(call: unknown[] | undefined): Record<string, unknown> {
  const init = call?.[1] as RequestInit | undefined;
  if (!init?.body) return {};
  try {
    return JSON.parse(init.body as string);
  } catch {
    return {};
  }
}

// Categories now carry id (D5) so selects can post category_id.
export const REFERENCE = {
  units: [{ number: "101", ownership_pct: 0.117 }],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
  ],
  categories: [
    { id: 19, name: "Other", type: "Expense" },
    { id: 17, name: "Insurance Premiums", type: "Expense" },
  ],
};

// A list response where one row is flagged for review.
export const TRANSACTIONS = {
  transactions: [
    {
      id: 7, account_number: "****9242", account_name: "Checking",
      post_date: "2026-01-16", check_number: null,
      description: "ZZQ UNRECOGNIZED VENDOR 5571",
      debit: 4200, credit: null, status: "Posted", balance: 45800,
      category: null, needs_review: 1,
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
};

export const RULES = {
  rules: [
    {
      id: 3, pattern: "Cintas", category_id: 12, category: "Cintas Fire Protection",
      account: null, amount_min: null, amount_max: null,
      priority: 100, confidence: 100, active: 1,
    },
  ],
};

export const SUGGEST = { pattern: "ZZQ UNRECOGNIZED VENDOR" };
