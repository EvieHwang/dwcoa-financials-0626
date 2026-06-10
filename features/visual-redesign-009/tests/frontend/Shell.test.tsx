// @scaffolding — names the app-shell theme toggle (a topbar button with an
// accessible name /theme|appearance|dark|light|sun|moon/i). /build may rename it,
// logging it in build-deviations.md, as long as a reachable theme control exists.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "@/App";
import { resetThemeState, routes, setPrefersDark, stubFetch } from "./helpers";

beforeEach(() => {
  resetThemeState();
  setPrefersDark(false);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  resetThemeState();
});

describe("app shell", () => {
  it("theme_toggle_present", async () => {
    stubFetch(routes("viewer"));
    render(<App />);
    expect(
      await screen.findByRole("button", {
        name: /theme|appearance|dark|light|sun|moon/i,
      }),
    ).toBeInTheDocument();
  });
});
