// @scaffolding — names the dues DOM surface (a "dues" region inside the dashboard,
// per-unit rows with money as USD, sharing the dashboard's "As of" date control).
// /build may refine markup, labels, and placement — logging it in
// build-deviations.md — as long as these BEHAVIORS hold: the view renders per-unit
// dues (ownership, carryover, annual, expected, paid, outstanding) from GET
// /api/dues as USD; changing the shared as-of date refetches /api/dues with the new
// as_of; both roles see the same read-only table; and a not-tracked payload renders
// a note instead of unit rows.
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
  DUES,
  DUES_NOT_TRACKED,
  REFERENCE,
  TRANSACTIONS,
  callsTo,
  stubFetch,
} from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// visual-redesign-009: Dues by unit is now its own nav screen (it was embedded in
// the dashboard); reaching it takes one nav step. The shared "As of" control still
// lives in the shell. Behavioral assertions are unchanged. Logged in
// build-deviations.md.
async function gotoDues() {
  const nav = await screen.findByRole("navigation");
  fireEvent.click(within(nav).getByRole("button", { name: /dues/i }));
}

function routes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/budgets": { body: BUDGETS },
    "/api/dashboard": { body: DASHBOARD },
    "/api/dues": { body: DUES },
    ...extra,
  };
}

// The dues region; flexible name so /build can label it.
function duesRegion() {
  return screen.getByRole("region", { name: /dues/i });
}

async function waitForDues() {
  // Unit 101 outstanding, formatted USD, proves the dues table loaded.
  await waitFor(() =>
    expect(screen.getAllByText(/\$4,540\.30/).length).toBeGreaterThan(0),
  );
}

describe("dues by unit", () => {
  it("renders_dues_rows_from_endpoint", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await gotoDues();
    await waitForDues();

    const region = duesRegion();
    // Unit number, ownership (11.7%), and the outstanding USD figure all render.
    expect(within(region).getByText(/101/)).toBeInTheDocument();
    expect(within(region).getByText(/11\.7\s*%/)).toBeInTheDocument();
    expect(within(region).getByText(/\$4,540\.30/)).toBeInTheDocument();
    // The paid figure ($2,000.00) renders too.
    expect(within(region).getByText(/\$2,000\.00/)).toBeInTheDocument();
  });

  it("as_of_change_refetches_dues", async () => {
    const fn = stubFetch(routes("viewer"));
    render(<App />);
    await gotoDues();
    await waitForDues();

    const initial = callsTo(fn, "/api/dues").length;
    expect(initial).toBeGreaterThan(0);
    const dateInput = screen.getByLabelText(/as of/i);
    fireEvent.change(dateInput, { target: { value: "2027-03-15" } });

    await waitFor(() => {
      const duesCalls = callsTo(fn, "/api/dues");
      expect(duesCalls.length).toBeGreaterThan(initial);
      // The refetch carries the new as-of date in its query string.
      expect(duesCalls.some((c) => c.url.includes("2027-03-15"))).toBe(true);
    });
  });

  it("viewer_sees_same_readonly_dues", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await gotoDues();
    await waitForDues();

    const region = duesRegion();
    expect(within(region).getByText(/\$4,540\.30/)).toBeInTheDocument();
    // No write control lives inside the dues table.
    expect(
      within(region).queryByRole("button", { name: /save|edit|lock|delete|upload/i }),
    ).toBeNull();
  });

  it("shows_not_tracked_note", async () => {
    stubFetch(routes("viewer", { "/api/dues": { body: DUES_NOT_TRACKED } }));
    render(<App />);
    await gotoDues();
    // Wait for the dues screen to settle (the not-tracked note renders).
    await waitFor(() =>
      expect(screen.getByText(/2025|not tracked|begins/i)).toBeInTheDocument(),
    );

    const region = duesRegion();
    // A clear "tracking begins 2025 / not tracked" note instead of unit rows.
    expect(within(region).getByText(/2025|not tracked|begins/i)).toBeInTheDocument();
    expect(within(region).queryByText(/\$4,540\.30/)).toBeNull();
  });
});
