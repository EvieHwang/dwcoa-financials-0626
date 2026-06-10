// @scaffolding — names the role-gating surface: the `admin-only` test-id marker,
// admin nav items (Review/Rules/Import), and the absence of any UI control that
// changes role. /build may restructure markup (logged in build-deviations.md) as
// long as these BEHAVIORS hold: role comes only from /api/auth/me, viewers see no
// admin nav/controls, admins do, and there is no role-switch affordance anywhere.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App from "@/App";
import { resetThemeState, routes, setPrefersDark, stubFetch } from "./helpers";

const OVERVIEW = /dashboard|finances|financial/i;

beforeEach(() => {
  resetThemeState();
  setPrefersDark(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  resetThemeState();
});

function findNavItem(name: RegExp): HTMLElement | null {
  const nav = screen.queryByRole("navigation");
  if (!nav) return null;
  return (
    within(nav).queryByRole("link", { name }) ??
    within(nav).queryByRole("button", { name })
  );
}

async function waitForOverview() {
  return screen.findByRole("region", { name: OVERVIEW });
}

describe("role gating (from auth only)", () => {
  it("no_role_switch_control", async () => {
    stubFetch(routes("admin"));
    render(<App />);
    await waitForOverview();
    // No segmented/radio/tab control that would switch the role in the UI. A
    // static role *label* (e.g. in the user chip) is fine; a selectable affordance
    // for the other role is the prototype-ism that must not ship.
    expect(screen.queryByRole("radio", { name: /treasurer|homeowner/i })).toBeNull();
    expect(screen.queryByRole("tab", { name: /treasurer|homeowner/i })).toBeNull();
    expect(screen.queryByRole("switch", { name: /treasurer|homeowner|role/i })).toBeNull();
  });

  it("viewer_no_admin_ui", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForOverview();
    expect(screen.queryByTestId("admin-only")).toBeNull();
    // Admin destinations are not reachable from the nav for a viewer.
    expect(findNavItem(/review/i)).toBeNull();
    expect(findNavItem(/rules/i)).toBeNull();
    expect(findNavItem(/import|upload/i)).toBeNull();
    // No write affordances anywhere for a viewer.
    expect(screen.queryByRole("button", { name: /upload/i })).toBeNull();
  });

  it("admin_sees_admin_ui", async () => {
    stubFetch(routes("admin"));
    render(<App />);
    await waitForOverview();
    expect(screen.getByTestId("admin-only")).toBeInTheDocument();
    expect(findNavItem(/review/i)).not.toBeNull();
    expect(findNavItem(/rules/i)).not.toBeNull();

    // Navigating to Import surfaces the upload affordances.
    const importNav = findNavItem(/import|upload/i);
    expect(importNav).not.toBeNull();
    fireEvent.click(importNav!);
    await waitFor(() =>
      expect(screen.getByLabelText(/csv|file|upload/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /upload/i })).toBeInTheDocument();
  });
});
