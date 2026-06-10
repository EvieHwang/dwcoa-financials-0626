// @scaffolding — names the nav surface: a `navigation` landmark whose items
// (link or button) carry the screen names, and that the default authenticated
// screen is the Overview/Dashboard. /build may choose router vs local state and
// label items as it likes (logged in build-deviations.md) as long as these
// BEHAVIORS hold: exactly one primary screen is shown at a time, switching nav
// swaps it (the prior screen leaves the accessibility tree), and every screen is
// reachable from the navigation landmark.
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

/** A nav item (link or button) inside the navigation landmark, or null. */
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

describe("nav-switched screens", () => {
  it("default_screen_is_overview", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForOverview();
    // Only the Overview shows by default — the Budget screen is not also mounted.
    expect(screen.queryByRole("region", { name: /budget/i })).toBeNull();
  });

  it("nav_swaps_single_screen", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForOverview();

    const budgetNav = findNavItem(/budget/i);
    expect(budgetNav).not.toBeNull();
    fireEvent.click(budgetNav!);

    // Budget screen appears...
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /budget/i })).toBeInTheDocument(),
    );
    // ...and the Overview is swapped out, not stacked beneath it.
    expect(screen.queryByRole("region", { name: OVERVIEW })).toBeNull();
  });

  it("screens_reachable_by_nav", async () => {
    stubFetch(routes("admin"));
    render(<App />);
    await waitForOverview();

    // Every primary screen is reachable from the nav for an admin.
    for (const name of [
      /overview|dashboard/i,
      /transactions/i,
      /dues/i,
      /budget/i,
      /my account/i,
      /review/i,
      /rules/i,
      /import|upload/i,
    ]) {
      expect(findNavItem(name)).not.toBeNull();
    }
  });
});
