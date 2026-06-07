// @scaffolding — names the budget-editor DOM surface (amount inputs labeled by
// category, save / copy-year / lock controls). /build may refine markup, labels,
// and placement (a tab, a route) — logging it in build-deviations.md — as long
// as these BEHAVIORS hold: amounts render as USD from GET /api/budgets; an admin
// save POSTs integer cents; copy into a non-empty year confirms then retries
// with overwrite; the lock toggle POSTs; a locked year is not editable; and a
// viewer sees no write controls.
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
    ...extra,
  };
}

async function waitForBudget() {
  // The overridden line's amount, formatted USD, proves the editor loaded.
  await waitFor(() =>
    expect(screen.getByText(/\$6,000\.00/)).toBeInTheDocument(),
  );
}

describe("budget editor", () => {
  it("renders_amounts_as_usd_from_endpoint", async () => {
    stubFetch(routes("admin"));
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText(/\$4,500\.00/)).toBeInTheDocument(),
    );
    expect(screen.getByText("Insurance Premiums")).toBeInTheDocument();
  });

  it("admin_save_posts_integer_cents", async () => {
    const fn = stubFetch(routes("admin"));
    render(<App />);
    await waitForBudget();

    // Edit the Insurance Premiums line to $5,000 and save it.
    const input = screen.getByLabelText(/insurance premiums.*amount/i);
    fireEvent.change(input, { target: { value: "5000" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      const posts = callsTo(fn, "/api/budgets", "POST");
      expect(posts.length).toBeGreaterThan(0);
      // Dollars converted to integer cents at the boundary.
      expect(posts.some((c) => (c.body as any)?.annual_amount === 500000)).toBe(
        true,
      );
    });
  });

  it("copy_year_into_nonempty_confirms_then_overwrites", async () => {
    // Copy is rejected 409 (target non-empty); the UI must confirm and retry
    // with overwrite:true.
    const fn = stubFetch(routes("admin", { "/api/budgets/copy": { status: 409 } }));
    render(<App />);
    await waitForBudget();

    fireEvent.click(screen.getByRole("button", { name: /copy/i }));

    // A confirmation surfaces after the 409.
    const confirm = await screen.findByRole("button", { name: /overwrite|confirm|yes/i });
    fireEvent.click(confirm);

    await waitFor(() => {
      const copies = callsTo(fn, "/api/budgets/copy", "POST");
      expect(copies.some((c) => (c.body as any)?.overwrite === true)).toBe(true);
    });
  });

  it("lock_toggle_posts_lock", async () => {
    const fn = stubFetch(routes("admin"));
    render(<App />);
    await waitForBudget();

    fireEvent.click(screen.getByRole("button", { name: /lock/i }));

    await waitFor(() =>
      expect(callsTo(fn, "/api/budgets/lock", "POST").length).toBeGreaterThan(0),
    );
  });

  it("locked_year_is_not_editable", async () => {
    stubFetch(
      routes("admin", {
        "/api/budgets": { body: { ...BUDGETS, locked: true, locked_at: "2025-01-01T00:00:00" } },
      }),
    );
    render(<App />);
    await waitForBudget();

    // No enabled amount input for editing a locked year.
    const input = screen.queryByLabelText(/insurance premiums.*amount/i);
    if (input) {
      expect(input).toBeDisabled();
    } else {
      // Acceptable alternative: a locked year renders amounts as static text.
      expect(screen.getByText(/\$4,500\.00/)).toBeInTheDocument();
    }
  });

  it("viewer_sees_no_write_controls", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForBudget();

    // The budget is visible, but no save / copy / lock controls for a viewer.
    const region =
      screen.queryByRole("region", { name: /budget/i }) ?? document.body;
    expect(
      within(region).queryByRole("button", { name: /save/i }),
    ).toBeNull();
    expect(
      within(region).queryByRole("button", { name: /copy/i }),
    ).toBeNull();
    expect(
      within(region).queryByRole("button", { name: /lock/i }),
    ).toBeNull();
  });
});
