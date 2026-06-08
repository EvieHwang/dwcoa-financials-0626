// @scaffolding — names the dashboard DOM surface (a "Dashboard"/"finances"
// region, an "As of" date control, and money rendered as USD). /build may refine
// markup, labels, placement (a tab, a route, a chart library) — logging it in
// build-deviations.md — as long as these BEHAVIORS hold: the view renders account
// balances / total cash / income & expense budget-vs-actual / reserve / chart from
// GET /api/dashboard as USD; changing the as-of date refetches with the new as_of;
// and both roles see the same read-only view (no admin-only control inside it).
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import App from "@/App";
import {
  BUDGETS,
  DASHBOARD,
  REFERENCE,
  TRANSACTIONS,
  callsTo,
  stubFetch,
} from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function routes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/budgets": { body: BUDGETS },
    "/api/dashboard": { body: DASHBOARD },
    ...extra,
  };
}

// The dashboard region; flexible name so /build can label it.
function dashboardRegion() {
  return screen.getByRole("region", { name: /dashboard|finances|financial/i });
}

async function waitForDashboard() {
  // Total cash, formatted USD, proves the dashboard loaded from the endpoint.
  await waitFor(() =>
    expect(screen.getAllByText(/\$9,000\.00/).length).toBeGreaterThan(0),
  );
}

describe("dashboard view", () => {
  it("renders_balances_and_summary_from_endpoint", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForDashboard();

    const region = dashboardRegion();
    // Account balance (Checking $2,500.00) and total cash ($9,000.00).
    expect(within(region).getByText(/\$2,500\.00/)).toBeInTheDocument();
    // Budget-vs-actual numbers: expense actual $500.00 and remaining $100.00.
    expect(within(region).getByText(/\$500\.00/)).toBeInTheDocument();
    expect(within(region).getByText(/\$100\.00/)).toBeInTheDocument();
    // Category names appear in the summary.
    expect(within(region).getByText(/Insurance Premiums/)).toBeInTheDocument();
    expect(within(region).getByText(/Dues 101/)).toBeInTheDocument();
  });

  it("renders_reserve_and_chart", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForDashboard();

    const region = dashboardRegion();
    // Reserve net $2,600.00 from the reserve_fund block.
    expect(within(region).getByText(/\$2,600\.00/)).toBeInTheDocument();
    // The monthly series is rendered in some observable form (the income/expense
    // numbers for an active month, e.g. February income $333.00).
    expect(within(region).getAllByText(/\$333\.00/).length).toBeGreaterThan(0);
  });

  it("as_of_change_refetches", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await waitForDashboard();

    const initial = callsTo(fn, "/api/dashboard").length;
    const dateInput = screen.getByLabelText(/as of/i);
    fireEvent.change(dateInput, { target: { value: "2030-03-15" } });

    await waitFor(() => {
      const dashCalls = callsTo(fn, "/api/dashboard");
      expect(dashCalls.length).toBeGreaterThan(initial);
      // The refetch carries the new as-of date in its query string.
      expect(dashCalls.some((c) => c.url.includes("2030-03-15"))).toBe(true);
    });
  });

  it("viewer_sees_same_readonly_dashboard", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForDashboard();

    const region = dashboardRegion();
    // The same financials render for a viewer, with no write control inside the
    // dashboard view.
    expect(within(region).getByText(/\$9,000\.00/)).toBeInTheDocument();
    expect(within(region).queryByRole("button", { name: /save|upload|lock|delete/i })).toBeNull();
  });
});
