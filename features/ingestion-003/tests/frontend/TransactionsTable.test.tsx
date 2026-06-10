// @scaffolding — names the transactions-table DOM surface (rows, year/account
// filter controls, paging). /build may refine markup/test-ids, logging it, as
// long as these BEHAVIORS hold: rows render from the list endpoint, changing a
// filter re-queries with that filter, and paging advances the offset.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "@/App";
import { stubFetch, calledUrls, REFERENCE, TRANSACTIONS } from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// visual-redesign-009: screens now sit behind sidebar navigation, so reaching the
// Transactions screen takes one nav step (the behavioral assertions below are
// otherwise unchanged). Logged in features/visual-redesign-009/build-deviations.md.
async function gotoTransactions() {
  const nav = await screen.findByRole("navigation");
  fireEvent.click(within(nav).getByRole("button", { name: /transactions/i }));
}

function routes(extra = {}) {
  return {
    "/api/auth/me": { body: { role: "viewer" } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    ...extra,
  };
}

describe("transactions table", () => {
  it("renders_rows_from_list_endpoint", async () => {
    stubFetch(routes());
    render(<App />);
    await gotoTransactions();
    await waitFor(() =>
      expect(screen.getByText("Dividend/Interest")).toBeInTheDocument(),
    );
    expect(screen.getByText("Check Payment")).toBeInTheDocument();
    // account name resolved, not the masked number alone
    expect(screen.getByText("Reserve Fund")).toBeInTheDocument();

    // R11 a11y (WCAG 2.1 AA, scoped): real column headers, not bare cells/divs
    const headers = screen.getAllByRole("columnheader");
    expect(headers.length).toBeGreaterThan(0);
    headers.forEach((h) => expect(h).toHaveAttribute("scope", "col"));
  });

  it("year_filter_requeries_with_year_param", async () => {
    const fn = stubFetch(routes());
    render(<App />);
    await gotoTransactions();
    await waitFor(() =>
      expect(screen.getByText("Dividend/Interest")).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText(/year/i), { target: { value: "2025" } });

    await waitFor(() =>
      expect(calledUrls(fn).some((u) => /[?&]year=2025\b/.test(u))).toBe(true),
    );
  });

  it("account_filter_requeries_with_account_param", async () => {
    const fn = stubFetch(routes());
    render(<App />);
    await gotoTransactions();
    await waitFor(() =>
      expect(screen.getByText("Check Payment")).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText(/account/i), {
      target: { value: "Checking" },
    });

    await waitFor(() =>
      expect(calledUrls(fn).some((u) => /[?&]account=Checking\b/.test(u))).toBe(true),
    );
  });

  it("paging_advances_offset", async () => {
    // total (5) exceeds the page so a next-page control is meaningful
    const fn = stubFetch(
      routes({
        "/api/transactions": {
          body: { ...TRANSACTIONS, total: 5, limit: 2, offset: 0 },
        },
      }),
    );
    render(<App />);
    await gotoTransactions();
    await waitFor(() =>
      expect(screen.getByText("Dividend/Interest")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() =>
      expect(calledUrls(fn).some((u) => /[?&]offset=2\b/.test(u))).toBe(true),
    );
  });
});
