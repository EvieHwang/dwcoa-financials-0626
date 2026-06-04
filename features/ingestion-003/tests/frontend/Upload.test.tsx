// @scaffolding — names the upload control's DOM surface (file-input label,
// "Upload" action, summary region) ahead of implementation. /build may refine
// the markup/test-ids, logging it, as long as these BEHAVIORS hold: admin-only
// visibility, POST to the upload endpoint, and a rendered result summary.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "@/App";
import { stubFetch, calledUrls, REFERENCE, TRANSACTIONS } from "./helpers";

const UPLOAD_PATH = "/api/transactions/upload";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function baseRoutes(role: "admin" | "viewer", extra = {}) {
  return {
    "/api/auth/me": { body: { role } },
    "/api/reference": { body: REFERENCE },
    "/api/transactions": { body: TRANSACTIONS },
    ...extra,
  };
}

describe("CSV upload control", () => {
  it("admin_sees_upload_input", async () => {
    stubFetch(baseRoutes("admin"));
    render(<App />);
    await waitFor(() =>
      expect(screen.getByLabelText(/csv|file|upload/i)).toBeInTheDocument(),
    );
  });

  it("viewer_does_not_see_upload_input", async () => {
    stubFetch(baseRoutes("viewer"));
    render(<App />);
    // wait for the authenticated shell to settle (a transaction row renders)
    await waitFor(() =>
      expect(screen.getByText("Dividend/Interest")).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText(/csv|file|upload/i)).not.toBeInTheDocument();
  });

  it("uploads_file_and_renders_summary", async () => {
    const fn = stubFetch(
      baseRoutes("admin", {
        [UPLOAD_PATH]: {
          body: {
            added: 2,
            skipped_duplicate: 1,
            unknown_account_count: 0,
            unknown_accounts: [],
            total: 3,
          },
        },
      }),
    );
    render(<App />);

    const input = (await screen.findByLabelText(/csv|file|upload/i)) as HTMLInputElement;
    const file = new File(["Account Number,Post Date\n"], "history.csv", {
      type: "text/csv",
    });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /upload/i }));

    // a POST went to the upload endpoint
    await waitFor(() => expect(calledUrls(fn)).toContain(UPLOAD_PATH));
    const uploadCall = fn.mock.calls.find(
      (c) => (typeof c[0] === "string" ? c[0] : String(c[0])) === UPLOAD_PATH,
    );
    expect((uploadCall?.[1] as RequestInit | undefined)?.method).toMatch(/post/i);

    // the result summary is shown to the user, in a region announced to AT (R11)
    const summary = await screen.findByTestId("upload-summary");
    expect(summary).toHaveAttribute("aria-live");
    expect(summary).toHaveTextContent(/added/i);
    expect(summary).toHaveTextContent(/2/);
    expect(summary).toHaveTextContent(/1/); // skipped duplicate
  });
});
