import { vi } from "vitest";

type Routes = Record<string, { status?: number; body?: unknown }>;

/**
 * Stub global fetch, routing by the pathname of the request URL.
 * Any unlisted route resolves 404 so missing wiring fails loudly.
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
