// @scaffolding — names the My Account DOM surface (a region labelled "My Account"
// inside the dashboard, a unit <select>, money as USD, sharing the dashboard's "As
// of" date control, the selected unit persisted in localStorage). /build may refine
// markup, labels, the localStorage key, and placement — logging it in
// build-deviations.md — as long as these BEHAVIORS hold: before a unit is chosen the
// section shows a prompt and does NOT call /api/account; selecting a unit fetches
// GET /api/account?unit=<n>&as_of=<dashboard as-of> and renders the statement as
// USD; the choice persists across a remount; changing the shared as-of refetches
// /api/account; both roles see the same read-only section; and a not-tracked payload
// renders a note instead of figures.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  ACCOUNT,
  ACCOUNT_NOT_TRACKED,
  BUDGETS,
  DASHBOARD,
  DUES,
  REFERENCE,
  TRANSACTIONS,
  callsTo,
  stubFetch,
} from "./helpers";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

// visual-redesign-009: My account is now its own nav screen (it was embedded in
// the dashboard); reaching it takes one nav step. The shared "As of" control still
// lives in the shell. Behavioral assertions are unchanged. Logged in
// build-deviations.md.
async function gotoAccount() {
  const nav = await screen.findByRole("navigation");
  fireEvent.click(within(nav).getByRole("button", { name: /my account/i }));
}

function routes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/budgets": { body: BUDGETS },
    "/api/dashboard": { body: DASHBOARD },
    "/api/dues": { body: DUES },
    "/api/account": { body: ACCOUNT },
    ...extra,
  };
}

// The My Account region; specifically "my account" so it doesn't match the
// dashboard's "Account balances" region.
function myAccountRegion() {
  return screen.findByRole("region", { name: /my account/i });
}

// $21,100.00 (remaining_balance 2,110,000) is the unique sentinel proving the
// statement loaded for the selected unit.
const SENTINEL = /\$21,100\.00/;

async function selectUnit(region: HTMLElement, value: string) {
  const select = within(region).getByRole("combobox");
  fireEvent.change(select, { target: { value } });
}

describe("my account", () => {
  it("shows_prompt_and_selector_before_selection", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await gotoAccount();
    const region = await myAccountRegion();

    // A prompt to pick a unit, and a selector listing the nine units.
    expect(within(region).getByText(/select your unit/i)).toBeInTheDocument();
    expect(within(region).getByRole("option", { name: "101" })).toBeInTheDocument();
    expect(within(region).getByRole("option", { name: "303" })).toBeInTheDocument();

    // No statement is fetched until a unit is chosen.
    expect(callsTo(fn, "/api/account").length).toBe(0);
    expect(within(region).queryByText(SENTINEL)).toBeNull();
  });

  it("selecting_unit_fetches_and_renders", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await gotoAccount();
    const region = await myAccountRegion();

    await selectUnit(region, "101");

    await waitFor(() =>
      expect(within(region).getByText(SENTINEL)).toBeInTheDocument(),
    );
    // The fetch carried the selected unit; guidance + a recent payment render too.
    expect(callsTo(fn, "/api/account").some((c) => c.url.includes("unit=101"))).toBe(
      true,
    );
    expect(within(region).getByText(/\$1,950\.00/)).toBeInTheDocument(); // standard monthly
    expect(within(region).getByText(/\$10,000\.00/)).toBeInTheDocument(); // recent payment
  });

  it("selection_persists_across_remount", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await gotoAccount();
    let region = await myAccountRegion();
    await selectUnit(region, "101");
    await waitFor(() =>
      expect(within(region).getByText(SENTINEL)).toBeInTheDocument(),
    );

    // Remount the whole app (new session) — the stored unit is restored and its
    // statement fetched without re-selecting.
    cleanup();
    render(<App />);
    await gotoAccount();
    region = await myAccountRegion();
    await waitFor(() =>
      expect(within(region).getByText(SENTINEL)).toBeInTheDocument(),
    );
    expect(within(region).queryByText(/select your unit/i)).toBeNull();
    expect(callsTo(fn, "/api/account").some((c) => c.url.includes("unit=101"))).toBe(
      true,
    );
  });

  it("as_of_change_refetches_account", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await gotoAccount();
    const region = await myAccountRegion();
    await selectUnit(region, "101");
    await waitFor(() =>
      expect(within(region).getByText(SENTINEL)).toBeInTheDocument(),
    );

    const before = callsTo(fn, "/api/account").length;
    const dateInput = screen.getByLabelText(/as of/i);
    fireEvent.change(dateInput, { target: { value: "2027-03-15" } });

    await waitFor(() => {
      const acctCalls = callsTo(fn, "/api/account");
      expect(acctCalls.length).toBeGreaterThan(before);
      // The refetch carries both the selected unit and the new as-of date.
      expect(
        acctCalls.some(
          (c) => c.url.includes("unit=101") && c.url.includes("2027-03-15"),
        ),
      ).toBe(true);
    });
  });

  it("viewer_sees_same_readonly_account", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await gotoAccount();
    const region = await myAccountRegion();
    await selectUnit(region, "101");
    await waitFor(() =>
      expect(within(region).getByText(SENTINEL)).toBeInTheDocument(),
    );

    // No write control lives inside the My Account section.
    expect(
      within(region).queryByRole("button", {
        name: /save|edit|lock|delete|upload|pay/i,
      }),
    ).toBeNull();
  });

  it("shows_not_tracked_note", async () => {
    stubFetch(routes("viewer", { "/api/account": { body: ACCOUNT_NOT_TRACKED } }));
    render(<App />);
    await gotoAccount();
    const region = await myAccountRegion();
    await selectUnit(region, "101");

    // A clear "tracking begins 2025 / not tracked" note instead of figures.
    await waitFor(() =>
      expect(
        within(region).getByText(/2025|not tracked|begins/i),
      ).toBeInTheDocument(),
    );
    expect(within(region).queryByText(SENTINEL)).toBeNull();
  });
});
