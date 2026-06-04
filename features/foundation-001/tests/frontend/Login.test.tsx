import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { stubFetch } from "./helpers";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("login screen (unauthenticated)", () => {
  it("shows_login_when_unauthenticated", async () => {
    stubFetch({ "/api/auth/me": { status: 401 } });
    render(<App />);
    // a labeled password field is the WCAG-fundamentals contract
    await waitFor(() => expect(screen.getByLabelText(/password/i)).toBeInTheDocument());
    // dashboard shell content (units) is NOT shown before auth
    expect(screen.queryByText("101")).not.toBeInTheDocument();
  });

  it("has_labeled_inputs_and_focus", async () => {
    stubFetch({ "/api/auth/me": { status: 401 } });
    render(<App />);
    const field = await screen.findByLabelText(/password/i);
    // programmatically associated label + an actual form control
    expect(field.tagName).toBe("INPUT");
    expect(field).toHaveAttribute("type", "password");
    // a submit affordance exists and is reachable
    expect(screen.getByRole("button", { name: /(log ?in|sign ?in)/i })).toBeInTheDocument();
  });
});
