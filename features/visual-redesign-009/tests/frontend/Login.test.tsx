// @scaffolding — names the re-skinned login surface (labelled password field,
// "Log in"/"Sign in" submit, no role selector). /build may restyle freely (logged
// in build-deviations.md) as long as these BEHAVIORS hold: submitting POSTs the
// password to /api/auth/login and maps a non-2xx to an error message, and the
// password (not a UI control) determines the role — so there is no role selector.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { callsTo, resetThemeState, setPrefersDark, stubFetch } from "./helpers";

beforeEach(() => {
  resetThemeState();
  setPrefersDark(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  resetThemeState();
});

describe("login (re-skinned)", () => {
  it("renders_login_form", async () => {
    stubFetch({ "/api/auth/me": { status: 401 } });
    render(<App />);
    const field = await screen.findByLabelText(/password/i);
    expect(field).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: /(log ?in|sign ?in)/i })).toBeInTheDocument();
  });

  it("no_role_selector_on_login", async () => {
    stubFetch({ "/api/auth/me": { status: 401 } });
    render(<App />);
    await screen.findByLabelText(/password/i);
    // The password determines the role server-side; no Treasurer/Homeowner picker.
    expect(screen.queryByRole("radio", { name: /treasurer|homeowner/i })).toBeNull();
    expect(screen.queryByRole("tab", { name: /treasurer|homeowner/i })).toBeNull();
  });

  it("submit_posts_password_and_errors", async () => {
    const fn = stubFetch({
      "/api/auth/me": { status: 401 },
      "/api/auth/login": { status: 401 },
    });
    render(<App />);
    const field = await screen.findByLabelText(/password/i);
    fireEvent.change(field, { target: { value: "hunter2" } });
    fireEvent.click(screen.getByRole("button", { name: /(log ?in|sign ?in)/i }));

    await waitFor(() => {
      const logins = callsTo(fn, "/api/auth/login", "POST");
      expect(logins.length).toBeGreaterThan(0);
      expect((logins[0].body as { password?: string }).password).toBe("hunter2");
    });
    // A non-2xx maps to the incorrect-password message (behavior preserved).
    expect(await screen.findByText(/incorrect password/i)).toBeInTheDocument();
  });
});
