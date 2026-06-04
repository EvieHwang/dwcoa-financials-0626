import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { stubFetch } from "./helpers";

const REFERENCE = {
  units: [
    { number: "101", ownership_pct: 0.117 },
    { number: "102", ownership_pct: 0.104 },
    { number: "103", ownership_pct: 0.112 },
    { number: "201", ownership_pct: 0.117 },
  ],
  accounts: [
    { name: "Savings" },
    { name: "Checking" },
    { name: "Reserve Fund" },
  ],
  categories: [{ name: "Dues 101" }, { name: "Grounds/Landscaping" }],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("dashboard shell (authenticated)", () => {
  it("renders_units_from_api", async () => {
    stubFetch({
      "/api/auth/me": { body: { role: "viewer" } },
      "/api/reference": { body: REFERENCE },
    });
    render(<App />);
    // real seeded data is rendered, not a hard-coded placeholder
    await waitFor(() => expect(screen.getByText("101")).toBeInTheDocument());
    expect(screen.getByText("201")).toBeInTheDocument();
    // login form is gone once authenticated
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it("hides_admin_controls_for_viewer", async () => {
    stubFetch({
      "/api/auth/me": { body: { role: "viewer" } },
      "/api/reference": { body: REFERENCE },
    });
    render(<App />);
    await waitFor(() => expect(screen.getByText("101")).toBeInTheDocument());
    expect(screen.queryByTestId("admin-only")).not.toBeInTheDocument();
  });

  it("shows_admin_controls_for_admin", async () => {
    stubFetch({
      "/api/auth/me": { body: { role: "admin" } },
      "/api/reference": { body: REFERENCE },
    });
    render(<App />);
    await waitFor(() => expect(screen.getByText("101")).toBeInTheDocument());
    expect(screen.getByTestId("admin-only")).toBeInTheDocument();
  });
});
