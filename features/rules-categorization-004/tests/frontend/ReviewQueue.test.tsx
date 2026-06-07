// @scaffolding — names the review-queue DOM surface (a labeled per-row category
// select, "Save" and "Create rule" actions, a suggested-pattern input, a review
// count badge) ahead of implementation. /build may refine markup/test-ids,
// logging it, as long as these BEHAVIORS hold: admin-only visibility, a count of
// flagged rows, Save -> PATCH /api/transactions/{id} with the chosen category,
// and Create-rule -> fetch the suggestion then POST /api/rules with it.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "@/App";
import {
  stubFetch, callTo, bodyOf, REFERENCE, TRANSACTIONS, RULES, SUGGEST,
} from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function baseRoutes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    "/api/rules": { body: RULES },
    "/api/rules/suggest": { body: SUGGEST },
    "/api/transactions/7": { body: { id: 7 } },
    ...extra,
  };
}

describe("review queue", () => {
  it("admin_sees_queue_with_count", async () => {
    stubFetch(baseRoutes("admin"));
    render(<App />);
    const queue = await screen.findByTestId("review-queue");
    // The flagged row is listed and the count (1) is announced.
    expect(within(queue).getByText(/ZZQ UNRECOGNIZED VENDOR/i)).toBeInTheDocument();
    expect(screen.getByTestId("review-count")).toHaveTextContent("1");
  });

  it("viewer_does_not_see_queue", async () => {
    stubFetch(baseRoutes("viewer"));
    render(<App />);
    // Wait for the authenticated shell to settle, then assert no queue.
    await waitFor(() =>
      expect(screen.getByText(/ZZQ UNRECOGNIZED VENDOR/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("review-queue")).not.toBeInTheDocument();
  });

  it("save_posts_manual_fix_for_the_row", async () => {
    const fn = stubFetch(baseRoutes("admin"));
    render(<App />);
    const queue = await screen.findByTestId("review-queue");

    // Choose a category and Save -> PATCH /api/transactions/7 with that category.
    const select = within(queue).getByLabelText(/categor/i);
    fireEvent.change(select, { target: { value: "19" } }); // "Other"
    fireEvent.click(within(queue).getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(callTo(fn, "/api/transactions/7", "PATCH")).toBeTruthy(),
    );
    expect(bodyOf(callTo(fn, "/api/transactions/7", "PATCH"))).toMatchObject({
      category_id: 19,
    });
  });

  it("create_rule_uses_suggested_pattern", async () => {
    const fn = stubFetch(baseRoutes("admin"));
    render(<App />);
    const queue = await screen.findByTestId("review-queue");

    // Open the create-rule affordance for the flagged row.
    fireEvent.click(within(queue).getByRole("button", { name: /create rule/i }));

    // The suggestion endpoint is consulted and its pattern pre-fills an editable
    // input the admin can change before saving.
    await waitFor(() =>
      expect(callTo(fn, "/api/rules/suggest")).toBeTruthy(),
    );
    const patternInput = (await screen.findByLabelText(/pattern/i)) as HTMLInputElement;
    await waitFor(() => expect(patternInput.value).toBe("ZZQ UNRECOGNIZED VENDOR"));

    // Submitting posts the rule with the (suggested) pattern.
    fireEvent.click(screen.getByRole("button", { name: /save rule|create/i }));
    await waitFor(() =>
      expect(callTo(fn, "/api/rules", "POST")).toBeTruthy(),
    );
    expect(bodyOf(callTo(fn, "/api/rules", "POST"))).toMatchObject({
      pattern: "ZZQ UNRECOGNIZED VENDOR",
    });
  });
});
