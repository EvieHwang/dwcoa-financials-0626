# Build deviations — Budgets (005)

Honest record of where the build diverged from the spec's design or corrected a
test. The spec's *behavioral requirements* were not changed.

## 1. Scoped the `@scaffolding` category-name query to the budget region

- **Test:** `BudgetEditor.test.tsx::renders_amounts_as_usd_from_endpoint`
- **Original:** `expect(screen.getByText("Insurance Premiums")).toBeInTheDocument();`
- **Corrected:** query within the budget region —
  `within(screen.getByRole("region", { name: /budget/i })).getByText("Insurance Premiums")`.
- **Why:** `getByText` is a *global, unique-match* query. The shared
  `helpers.REFERENCE.categories` list (which includes "Insurance Premiums") is
  also rendered as `<option>`s by the admin rules-editor / review-queue selects
  that the same authenticated shell mounts. So once the budget editor renders the
  category name in its own table, "Insurance Premiums" exists **twice** in the
  document (one `<option>`, one budget `<td>`), and the global `getByText` throws
  `MultipleElementsFound` — it could never pass for an admin shell that also shows
  the rules editor, independent of the budget implementation.
- **Latitude used:** the test is tagged `@scaffolding` (markup/label/placement and
  the DOM-targeting surface may be refined as long as the asserted *behavior*
  holds). The asserted behavior — "the budget editor renders the category name,
  with amounts formatted as USD from `GET /api/budgets`" — is unchanged; only the
  query was tightened to the budget region. This is consistent with the suite's
  own design: the sibling `viewer_sees_no_write_controls` test already targets
  `screen.queryByRole("region", { name: /budget/i })`, so the authors intended a
  `region`-roled budget container to exist.
- **Spec-authoring lesson (for `/retro`):** a frontend scaffolding test that
  asserts a domain string with a *global* `getByText` is fragile in a
  single-page shell where multiple sections render the same reference data
  (category names appear in both editors and `<select>` options). Prefer
  region-scoped queries (`within(getByRole("region", …))`) for any text that the
  shared reference set can render in more than one place.

## Design notes (no behavioral divergence)

- The proration engine landed at `app.proration` with the exact
  `effective_timing` / `prorated_ytd` names and signatures the `@scaffolding`
  seam named — no refinement was needed.
- The HTTP surface (`app/routers/budgets.py`), business logic
  (`app/budgets.py`), and engine match the spec's component/seam design as
  written; the `@frozen` R1–R6 field names and status codes are used verbatim.
