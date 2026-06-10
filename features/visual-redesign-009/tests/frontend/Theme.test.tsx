// @scaffolding — names the theme surface: a topbar toggle (accessible name
// /theme|appearance|dark|light|sun|moon/i) and a dark indicator on <html> (the
// `.dark` class and/or data-theme="dark"). /build may rename the toggle or change
// the exact persistence key/attribute, logging it in build-deviations.md, as long
// as these BEHAVIORS hold: first load with no stored preference follows the OS
// prefers-color-scheme; the chosen theme persists across reloads; and a missing
// matchMedia never throws (defaults to light).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { resetThemeState, rootIsDark, routes, setPrefersDark, stubFetch } from "./helpers";

const TOGGLE = /theme|appearance|dark|light|sun|moon/i;

beforeEach(() => {
  resetThemeState();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  resetThemeState();
});

async function waitForShell() {
  // The theme toggle lives in the authenticated shell; its presence proves the
  // shell mounted and the theme has been applied.
  return screen.findByRole("button", { name: TOGGLE });
}

describe("theme", () => {
  it("defaults_to_os_dark_scheme", async () => {
    setPrefersDark(true);
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForShell();
    await waitFor(() => expect(rootIsDark()).toBe(true));
  });

  it("light_when_os_light", async () => {
    setPrefersDark(false);
    stubFetch(routes("viewer"));
    render(<App />);
    await waitForShell();
    expect(rootIsDark()).toBe(false);
  });

  it("no_matchmedia_defaults_light", async () => {
    setPrefersDark(null); // no window.matchMedia at all
    // Guard: prove the deletion actually took, so this test can't silently pass
    // against an implementation that calls a still-present matchMedia.
    expect(window.matchMedia).toBeUndefined();
    stubFetch(routes("viewer"));
    expect(() => render(<App />)).not.toThrow();
    await waitForShell();
    expect(rootIsDark()).toBe(false);
  });

  it("persists_across_remount", async () => {
    setPrefersDark(false); // OS light, so any dark state must come from the user
    stubFetch(routes("viewer"));
    const first = render(<App />);
    const toggle = await waitForShell();

    // Switch to dark.
    toggle.click();
    await waitFor(() => expect(rootIsDark()).toBe(true));

    // The preference must land in a real persistence layer (localStorage), not an
    // in-memory module variable that a true browser reload would lose. We assert
    // something was written without pinning the key (the key is @scaffolding).
    expect(localStorage.length).toBeGreaterThan(0);

    // Tear down and clear ONLY the root indicator (keep the persisted preference),
    // so a restored dark theme can only come from storage, not leftover DOM state.
    first.unmount();
    cleanup();
    document.documentElement.classList.remove("dark");
    document.documentElement.removeAttribute("data-theme");

    render(<App />);
    await waitForShell();
    await waitFor(() => expect(rootIsDark()).toBe(true));
  });
});
