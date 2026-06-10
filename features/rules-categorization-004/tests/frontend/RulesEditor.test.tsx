// @scaffolding — names the rules-editor DOM surface (a rules table with real
// column headers, a create form with labeled pattern + category, and per-row
// delete) ahead of implementation. /build may refine markup/test-ids, logging it,
// as long as these BEHAVIORS hold: admin-only visibility, rows rendered from
// GET /api/rules, create -> POST /api/rules, delete -> DELETE /api/rules/{id},
// and accessible (scope="col") table headers.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "@/App";
import { stubFetch, callTo, bodyOf, REFERENCE, TRANSACTIONS, RULES, SUGGEST } from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// visual-redesign-009: the rules editor is now an admin nav screen; reaching it
// (or the Transactions screen, for the viewer-absence check) takes one nav step.
// Behavioral assertions are unchanged. Logged in build-deviations.md.
async function gotoNav(name: RegExp) {
  const nav = await screen.findByRole("navigation");
  fireEvent.click(within(nav).getByRole("button", { name }));
}

function baseRoutes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/rules": { body: RULES },
    "/api/rules/suggest": { body: SUGGEST },
    "/api/rules/3": { body: { ok: true } },
    ...extra,
  };
}

describe("rules editor", () => {
  it("admin_sees_rules_table_with_accessible_headers", async () => {
    stubFetch(baseRoutes("admin"));
    render(<App />);
    await gotoNav(/rules/i);
    const editor = await screen.findByTestId("rules-editor");

    // The seeded rule renders (pattern + its category).
    expect(within(editor).getByText("Cintas")).toBeInTheDocument();
    expect(within(editor).getByText(/Cintas Fire Protection/i)).toBeInTheDocument();

    // a11y (R11): real column headers, not <div>s.
    const headers = within(editor).getAllByRole("columnheader");
    expect(headers.length).toBeGreaterThan(0);
    headers.forEach((h) => expect(h).toHaveAttribute("scope", "col"));
  });

  it("viewer_does_not_see_rules_editor", async () => {
    stubFetch(baseRoutes("viewer"));
    render(<App />);
    await gotoNav(/transactions/i);
    await waitFor(() =>
      expect(screen.getByText(/ZZQ UNRECOGNIZED VENDOR/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("rules-editor")).not.toBeInTheDocument();
  });

  it("create_rule_posts_pattern_and_category", async () => {
    const fn = stubFetch(baseRoutes("admin"));
    render(<App />);
    await gotoNav(/rules/i);
    const editor = await screen.findByTestId("rules-editor");

    fireEvent.change(within(editor).getByLabelText(/pattern/i), {
      target: { value: "SEATTLE CITY LIGHT" },
    });
    fireEvent.change(within(editor).getByLabelText(/categor/i), {
      target: { value: "19" }, // "Other"
    });
    fireEvent.click(within(editor).getByRole("button", { name: /add rule|create/i }));

    await waitFor(() => expect(callTo(fn, "/api/rules", "POST")).toBeTruthy());
    expect(bodyOf(callTo(fn, "/api/rules", "POST"))).toMatchObject({
      pattern: "SEATTLE CITY LIGHT",
      category_id: 19,
    });
  });

  it("delete_rule_calls_endpoint", async () => {
    const fn = stubFetch(baseRoutes("admin"));
    render(<App />);
    await gotoNav(/rules/i);
    const editor = await screen.findByTestId("rules-editor");

    fireEvent.click(within(editor).getByRole("button", { name: /delete|remove/i }));
    await waitFor(() =>
      expect(callTo(fn, "/api/rules/3", "DELETE")).toBeTruthy(),
    );
  });
});
