import { vi } from "vitest";

type Routes = Record<string, { status?: number; body?: unknown }>;

/**
 * Stub global fetch, routing by the pathname of the request URL (query string
 * ignored for matching, so filtered requests still resolve). Returns the mock so
 * tests can assert which URLs (with query params) were requested. Any unlisted
 * route resolves 404 so missing wiring fails loudly.
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

/** URLs (with query strings) seen by the fetch mock — for filter/pagination asserts. */
export function calledUrls(fn: ReturnType<typeof stubFetch>): string[] {
  return fn.mock.calls.map((c) => {
    const input = c[0] as RequestInfo | URL;
    return typeof input === "string" ? input : input.toString();
  });
}

export const REFERENCE = {
  units: [{ number: "101", ownership_pct: 0.117 }],
  accounts: [
    { name: "Savings", masked_number: "****7145" },
    { name: "Checking", masked_number: "****9242" },
    { name: "Reserve Fund", masked_number: "****9226" },
  ],
  categories: [{ name: "Dues 101", type: "Income" }],
};

export const TRANSACTIONS = {
  transactions: [
    {
      id: 2, account_number: "****9226", account_name: "Reserve Fund",
      post_date: "2026-01-05", check_number: null, description: "Dividend/Interest",
      debit: null, credit: 2515, status: "Posted", balance: 12126832, category: null,
    },
    {
      id: 1, account_number: "****9242", account_name: "Checking",
      post_date: "2025-09-20", check_number: null, description: "Check Payment",
      debit: 30000, credit: null, status: "Posted", balance: 670000, category: null,
    },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};
