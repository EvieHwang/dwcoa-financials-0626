# Spec — Visual redesign (009)

Re-skin the entire DWCOA Financials frontend to the modern-fintech design in
`frontend/design/`, decompose the monolithic `App.tsx` into primitives + screen
components, and replace the all-on-one-page layout with a sidebar-driven
nav-switched SPA — **with zero change to API calls, financial logic, data shapes,
or authorization.** The design package is the look-and-feel source of truth; where
it conflicts with the live data shapes or the app's real behavior, **the live
behavior wins** (per `frontend/design/README.md` § Data Mapping).

This is a frontend-only feature: **no backend code and no backend tests.**

---

## Behavioral requirements

### Reuse (no change)
Everything below is reused exactly as it exists today and must not be altered by
this feature. Tests assert these still hold; the design only changes how they look.

- **All API calls** — paths, methods, query params, bodies, and response handling
  in `App.tsx` are unchanged (`/api/auth/me`, `/api/auth/login`, `/api/auth/logout`,
  `/api/reference`, `/api/dashboard`, `/api/dues`, `/api/account`,
  `/api/transactions` incl. `?needs_review=true` and pagination, `/api/budgets`,
  `/api/budgets/copy`, `/api/budgets/lock`, `/api/rules`, `/api/rules/suggest`,
  `/api/transactions/upload`, `PATCH /api/transactions/:id`).
- **Money** — integer cents at the boundary; `centsToUsd` (cents/100 →
  `toLocaleString` USD) is the only formatter. No new client-side money math.
- **Proration** — `prorated_budget` is server-computed; the dashboard pace marker is
  `prorated_budget / annual_budget`, never recomputed on the client.
- **Ownership** — dashboard units use `ownership_pct` (×100 for %); dues use
  `ownership_per_mille` (÷10 for %). Each screen keeps the conversion it already uses.
- **`dues_tracked` flag** — gates the existing pre-2025 "tracking begins 2025" note
  on Dues by unit and My account.
- **Per-unit selection** — My account persists the selected unit to `localStorage`
  key `dwcoa.my-account.unit`; selection is a convenience, not an auth boundary.
- **Pagination** — Transactions paginate server-side via `limit`/`offset`; changing
  filters resets `offset` to 0.

### US-1 — Themed app shell (all users)
**As** any logged-in user, **I want** the app presented in the new visual language
with a persistent sidebar and a working light/dark theme, **so that** the dashboard
is legible and trustworthy.

Acceptance:
- The authenticated view renders inside an app shell: a sidebar with grouped
  navigation, a topbar (page title/subtitle, theme toggle), and a content area.
- A **theme toggle** control switches between light and dark. The toggle has an
  accessible name (matches `/theme|appearance|dark|light/i`).
- On first load with no stored preference, the theme follows the OS
  `prefers-color-scheme` (dark scheme → dark theme).
- The chosen theme **persists across reloads** (stored client-side); a remount with a
  stored preference restores it regardless of OS scheme.
- When the theme is dark, the document root reflects it in a way Tailwind's
  `darkMode` and the token CSS both key off (the `.dark` class and/or
  `data-theme="dark"` on `<html>`); when light, neither indicates dark.

### US-2 — Nav-switched screens (all users)
**As** a user, **I want** to move between screens from the sidebar, **so that** I see
one focused screen at a time instead of one long page.

Acceptance:
- Navigation shows **one primary screen at a time**. The default authenticated
  screen is the **Overview** (dashboard).
- Each primary screen is reachable via an accessible nav control whose name matches
  the screen (Overview/Dashboard, Transactions, Dues, Budget, My account, and — for
  admins — Review queue, Rules, Import).
- Activating a nav control makes that screen's region present and removes the
  previously-shown primary screen's region from the accessibility tree (true screen
  swap, not stacking).
- The sidebar collapses to a drawer toggled by a control (accessible name matches
  `/menu|navigation/i`) below the narrow breakpoint; this is a presentation detail
  not asserted pixel-wise.
- The **"As of" date is a single, app-level control that lives in the shell** (topbar),
  not inside any one screen, and **persists across screen swaps**. Overview, Dues, and
  My account all read this one shared as-of; changing it refetches whichever of those
  screens is currently active. This preserves today's single-control refetch behavior
  (see Reuse) — see **Design → Shared "As of"**.

### US-3 — Role-gated UI from auth only (all users)
**As** the system, **I want** the role to come only from `/api/auth/me`, **so that**
a viewer can never see or reach admin controls and role can't be toggled in the UI.

Acceptance:
- Role is read from `GET /api/auth/me`. There is **no UI control that changes role**
  (the prototype's Treasurer/Homeowner segmented control is not present, anywhere,
  including on Login).
- For a **viewer**: admin-only nav items (Review queue, Rules, Import) and admin-only
  controls (Upload, budget edit inputs, Save/Lock/Copy, rule create/delete) are
  absent; the `admin-only` marker is absent.
- For an **admin**: those nav items and controls are present and reachable; the
  `admin-only` marker is present.
- Read screens (Overview, Transactions, Dues, My account) contain no write controls
  for either role.

### US-4 — Login re-skin (unauthenticated)
**As** a returning user, **I want** the two-panel branded login, **so that** signing
in matches the rest of the app.

Acceptance:
- The login screen renders the password form (accessible name "Log in"), a labelled
  password field (`/password/i`), and a submit button (`/log ?in|sign ?in/i`).
- Behavior is unchanged: submitting POSTs `/api/auth/login {password}`; 200 → refresh
  auth; 429 → rate-limit message; other non-2xx → "Incorrect password." (No new
  client-side validation is added — the existing submit behavior is preserved exactly;
  the design's "error on empty" nicety is out of scope as it would change behavior.)
- No role selector on login (the password determines role server-side).

### US-5 — Every screen re-skinned, behavior preserved (all users)
**As** the board and homeowners, **I want** all existing screens restyled without any
change to the numbers or flows, **so that** the data stays correct.

Acceptance — each screen renders in the new design and preserves its existing
behavior and accessible anchors (the catalogue in **Design → Preservation contract**
is the authority):
- **Overview/Dashboard** — KPIs, cash-flow chart, reserve ring, budget-vs-actual
  meters with pace marker, account balances, dues snapshot; `as_of` change refetches
  `/api/dashboard` and `/api/dues` with the new date.
- **Transactions** — table with Year and Account filters and server pagination
  (Next/Prev); filter change resets offset and refetches.
- **Dues by unit** — per-unit table with status badges; `dues_tracked===false` shows
  the pre-2025 note instead of rows.
- **Budget** — read-only for viewers; for admins, editable amount inputs, Save
  (per-edited-line POST in integer cents), Copy-year (409 → confirm modal →
  `overwrite:true`), Lock/Unlock; a locked year is not editable.
- **My account** — unit `<combobox>` (options include the seeded units), statement,
  payment guidance; selection persists to `localStorage`; `dues_tracked===false`
  shows the pre-2025 note.
- **Review queue** (admin) — table with per-row Category select and Save; Create rule
  pre-fills a pattern from `/api/rules/suggest`; saving PATCHes the transaction.
- **Rules** (admin) — new-rule form (Pattern + Category + Add) and rules table with
  Delete.
- **Import** (admin) — file input + Upload; the summary panel renders the response
  counts and any unknown accounts; server `detail` errors surface as an alert.

### Edge cases & failure modes
- **No stored theme + no `matchMedia`** (older/headless env): default to light, never
  throw.
- **Reduced motion**: meters/ring/bars must rest at their final visible state with
  motion disabled — never gate content visibility on an entrance animation (a paused
  or disabled animation still shows full content). Honor `prefers-reduced-motion`.
- **Loading / empty / error states** preserved per screen (e.g. review queue empty
  state, upload error alert, login error text).
- **Auth loading and unauthenticated** states render without flashing admin UI.
- **Narrow viewport**: sidebar becomes a drawer; content remains usable; no horizontal
  scroll of the whole page.

### Out of scope
Per declaration: no API/financial-logic/auth changes; no accent or density prefs
(light/dark only); no print/PDF (already cut); no new screens or features; the rules
"Active toggle" stays visual-only or omitted (API has no endpoint); no component-
library migration; no native mobile.

---

## Design

### Architecture
`frontend/src/App.tsx` is decomposed into:
- **Tokens & theme** — light/dark design tokens as CSS variables plus a Tailwind
  theme extension; fonts self-hosted via `@fontsource/schibsted-grotesk` and
  `@fontsource/jetbrains-mono` (not the Google CDN); a `tnum` (tabular-nums) utility.
- **Primitives** — `Card`, `StatCard`, `Badge`, `Table`, `Button`, `Meter`, `Ring`,
  `BarChart`, `StackBar`, `Toast`, `Modal`, built on Tailwind + the tokens.
- **App shell** — `Sidebar`, `Topbar`, theme toggle, and nav-switched routing that
  shows one screen at a time; role-gated nav from `/api/auth/me`.
- **Screen components** — one per screen, each consuming the **same hooks/fetch/handler
  logic that exists in `App.tsx` today**, unchanged. Icons via `lucide-react`.

The decomposition is internal; the seams that matter externally are (a) the API
calls (unchanged) and (b) the accessible DOM surface the suites observe (preserved —
see below).

**Behavioral properties the design must hold:**
- *Theme seam:* a single source of truth for theme drives both the root indicator and
  the persisted value; reading the persisted value on mount and the OS scheme as the
  default are the only inputs. No screen component sets theme independently.
- *Routing seam:* exactly one primary screen is mounted in the content area at a time;
  switching unmounts the prior screen. Nav state is local UI state (no router required,
  though one is allowed); it does not affect any fetch.
- *Role seam:* role flows from auth into the shell, which decides nav/control
  visibility. No component derives role from anything client-settable.
- *Data seam:* screen components are render-only over the existing fetch results;
  they do not transform money beyond `centsToUsd`, do not recompute proration, and
  respect the per-endpoint ownership conversion.

### Shared "As of"
Today `Dashboard` (App.tsx ~519–606) owns the only `as_of` state and its one
`/as of/i` control, and renders `DuesByUnit` and `MyAccount` as children — so all
three share one as-of and three prior tests assert that changing that single control
refetches `/api/dashboard`, `/api/dues`, and `/api/account`. The nav-switched model
makes Dues and My account **separate screens**, so the shared control is lifted into
the **shell (topbar)** as a single app-level as-of:
- There is exactly **one** `/as of/i` control in the whole app, in the shell; it
  persists across screen swaps and is **not** inside any screen's region (so a screen
  swap, e.g. the `Nav` test asserting the Overview region unmounts, is unaffected).
- Changing it refetches the **active** screen's data with the new date (Overview →
  `/api/dashboard` + `/api/dues` snapshot as today's Dashboard does; Dues screen →
  `/api/dues`; My account screen → `/api/account`).
- **Behavioral preservation:** at the user level the behavior is identical — pick an
  as-of, the data reflects it. The only non-user-facing change is that inactive
  screens no longer refetch in the background (only the mounted screen does); no test
  asserts cross-screen background refetch, so this is invisible to the suite. The 3
  coupling tests (`dashboard-006 as_of_change_refetches`,
  `dues-by-unit-007 as_of_change_refetches_dues`,
  `my-account-008 as_of_change_refetches_account`) keep their assertions verbatim and
  gain only the sanctioned navigation step to reach the target screen (Overview is
  default and needs none).

### Preservation contract (the no-behavior-change safety net)
The 8 prior feature suites query purely by semantics (roles, accessible names,
labels, test-ids — verified: zero structural/`className`/`querySelector` assertions).
The redesign **must preserve every anchor below**, by accessible name/role/label/
test-id (exact text may change only where the suite uses a tolerant regex). These
suites are tagged `@scaffolding` and their headers already permit placement to become
"a tab, a route"; because screens now sit behind navigation, **`/build` adds a single
navigation step** to each prior-suite test that targets a non-default screen — the
behavioral assertions are otherwise unchanged — and logs each such edit in
`features/visual-redesign-009/build-deviations.md`. No behavioral assertion in those
suites may be weakened or removed.

Anchors to preserve:

| Surface | Anchor (role / label / test-id) |
|---|---|
| Login form | form accessible-name **"Log in"**; label **`/password/i`**; submit button **`/log ?in|sign ?in/i`** |
| Dashboard | region **`/dashboard|finances|financial/i`**; sub-regions "Account balances", "Reserve fund", "Monthly cashflow"; summary regions **`/…summary/i`** |
| Shared As-of | **exactly one** `/as of/i` control, app-level in the **shell** (not inside any screen region); read by Overview, Dues, and My account; changing it refetches the active screen |
| Units | unit numbers from `/api/reference` rendered as text (e.g. "101", "201") **on the default Overview screen, with no navigation** (foundation-001 asserts them on initial render); there is no standalone "Units" nav screen |
| Transactions | year filter label **`/year/i`**; account filter label **`/account/i`**; pagination button **`/next/i`** (and prev); `columnheader`s |
| Dues by unit | region **`/dues/i`**; pre-2025 note text **`/2025|not tracked|begins/i`** when not tracked |
| Budget | region **`/budget/i`**; per-line amount input label **`/<category> amount/i`**; buttons **`/save/i`**, **`/copy/i`**, **`/lock/i`**; copy-confirm button **`/overwrite|confirm|yes/i`**; locked-year lock status |
| My account | region **`/my account/i`**; unit `combobox` with `option`s for seeded units; select label **`/your unit/i`** |
| Review queue | test-id **`review-queue`**; test-id **`review-count`**; row category select label **`/categor/i`**; buttons **`/save/i`**, **`/create rule/i`** |
| Rules editor | test-id **`rules-editor`**; pattern label **`/pattern/i`**; category label **`/categor/i`**; add button **`/add rule|create/i`**; delete button **`/delete|remove/i`**; save-rule button **`/save rule|create/i`** |
| Import | file input label **`/csv|file|upload/i`**; upload button **`/upload/i`**; test-id **`upload-summary`** |
| Shell (admin) | test-id **`admin-only`** present for admins, absent for viewers |

Because the suites assert their region/test-id is present (often without navigating),
`/build` either makes the targeted screen the active one before the assertion (the
added nav step) or, for anchors expected on the default screen, ensures they appear on
Overview. The Overview is the default screen; the `admin-only` marker and units must be
reachable per the table.

**Additional load-bearing invariants `/build` must preserve (the prior suites assert
these and the redesign can silently break them):**
- **No write control inside read regions.** `dashboard-006`, `dues-by-unit-007`,
  `my-account-008`, and `budgets-005` (viewer) assert that their region contains **no**
  button matching `/save|upload|lock|delete|edit|pay/i`. Do not place such a control
  (including shell affordances) inside those regions for either role.
- **Shell control names must not collide with screen write-actions.** Persistent shell
  controls (theme toggle, logout, menu/drawer, nav items) must **not** carry accessible
  names matching `/save|upload|lock|delete|copy|next|create rule|add rule/i`, so the
  global (unscoped) button lookups in the prior suites resolve to the screen, not the
  shell. Nav items are reached via the `navigation` landmark.
- **Scope added assertions to the active screen.** When `/build` adds a nav step to a
  prior test and the subsequent assertion uses an unscoped query whose name could match
  more than one mounted element, scope it to the active screen's region/test-id (most
  prior suites already do via `within(region|queue|editor)`); never weaken or delete the
  behavioral assertion itself. Log every prior-suite edit in `build-deviations.md`.
- **Unique-or-scoped text.** Unit-number text on Overview (e.g. "101") must be unique
  within the rendered Overview or the prior `getByText("101")` will throw on ambiguity;
  keep co-mounted duplicate numbers out of Overview or scope them.

### Tokens & accessibility
- Token values come from `frontend/design/styles.css` / README; evergreen brand only.
- **WCAG 2.1 AA**: body and meaningful-UI text meet ≥4.5:1 (≥3:1 for large text and
  essential non-text indicators) in **both** themes. The muted `--ink-3` on its
  surfaces and amber-on-soft combinations are checked against AA before locking;
  status is never conveyed by color alone (badges carry text/icon).
- Focus-visible rings on all interactive controls; min 44px tap targets on mobile.

- **Dark indicator must match Tailwind.** `tailwind.config.js` is `darkMode:"class"`,
  so the `.dark` class is what activates `dark:` variants. If `/build` drives dark mode
  by a `data-theme` attribute instead, it **must** also update `darkMode` (e.g.
  `["selector", '[data-theme="dark"]']`) or add the `.dark` class — otherwise dark
  styling silently never activates while the theme tests (tolerant of either indicator)
  still pass. The token CSS and the Tailwind `darkMode` selector must agree.

### Standards-creep check
WCAG 2.1 AA already applies project-wide (constitution + declaration). This feature
absorbs it for the surfaces it builds — contrast in both themes, focus-visible,
reduced-motion, accessible names. Two of these are **verified manually, not by the
automated suite**, and are called out so the gap is explicit rather than implied-covered:
- **Contrast (≥4.5:1 text / ≥3:1 large+essential, both themes):** jsdom does not compute
  color/contrast, so this is a manual check against the locked tokens — `--ink-3` on its
  surfaces and amber-on-soft especially — and a `/build` acceptance item, not a test.
- **Reduced motion:** jsdom does not compute layout/opacity and `getByText` finds
  `opacity:0` nodes, so a "content hidden behind an entrance animation" defect would pass
  the suites. `/build` must ensure always-on content (chart values, meters, ring,
  balances) renders at its final visible state with no `opacity:0`/visibility gating, and
  honors `prefers-reduced-motion`; verified manually.

This feature does **not** undertake a full external WCAG audit of pre-existing copy or a
formal accessibility certification; that would exceed a re-skin. Surfaced here rather
than silently absorbed.

### Deviations & reuse
- **Deviation (recorded):** custom primitives on Tailwind + CSS variables instead of
  the constitution's default shadcn/ui — justified by the bespoke fintech look and
  custom charts (meters, ring, bars) that a component library would not provide. Logged
  in the decision log.
- **Deviation (recorded):** print-clean dashboard + matching PDF export, a constitution
  architectural principle and quality gate, is retired at the project level (it was
  never implemented; dashboard-006 had already cut it locally). The constitution
  principle and gate are softened and a decision-log row added.
- **Reuses pattern:** the entire fetch/auth/handler layer of `App.tsx` (auth state
  machine, per-section reload tokens, `centsToUsd`, pagination, role gating, upload
  handler, budget edit/save/copy/lock, rule create/delete, review save+suggest) is
  reused unchanged — this is genuine, complete reuse of the data layer; only markup
  and styling change.

---

## Testing

Runner: **Vitest** (frontend), per constitution § Testing. This feature ships only
`features/visual-redesign-009/tests/frontend/`. Tests import the app via the `@/`
alias and pull React / Testing Library / Vitest through the external-dep aliases in
`frontend/vite.config.ts`. Per project convention, **`/build` (not this spec PR)** adds
`"../features/visual-redesign-009/tests/frontend/**/*.test.{ts,tsx}"` to
`frontend/vite.config.ts` → `test.include`, so the spec PR stays green.

The 8 prior suites remain the behavior-preservation proof; this feature's new tests
assert only the behavior the redesign introduces.

---

## Coverage

| Requirement / seam | Test(s) |
|---|---|
| US-1 theme toggle present & accessible | `Shell.test.tsx › theme_toggle_present` |
| US-1 dark default from `prefers-color-scheme` | `Theme.test.tsx › defaults_to_os_dark_scheme` |
| US-1 theme persists across remount | `Theme.test.tsx › persists_across_remount` |
| US-1 light when OS light & no stored pref; no throw without matchMedia | `Theme.test.tsx › light_when_os_light`, `› no_matchmedia_defaults_light` |
| US-2 default screen is Overview | `Nav.test.tsx › default_screen_is_overview` |
| US-2 nav swaps one screen at a time | `Nav.test.tsx › nav_swaps_single_screen` |
| US-2 each screen reachable via accessible nav | `Nav.test.tsx › screens_reachable_by_nav` |
| US-3 no role-switch control anywhere | `Role.test.tsx › no_role_switch_control`, `Login.test.tsx › no_role_selector_on_login` |
| US-3 viewer sees no admin nav/controls/marker | `Role.test.tsx › viewer_no_admin_ui` |
| US-3 admin sees admin nav/controls/marker | `Role.test.tsx › admin_sees_admin_ui` |
| US-4 login re-skin keeps form + behavior | `Login.test.tsx › renders_login_form`, `› submit_posts_password_and_errors` |
| US-5 preservation contract (whole) | the 8 prior suites (unchanged assertions; `/build` adds nav steps) |
| US-5 shared As-of refetch preserved | `dashboard-006 as_of_change_refetches` (default screen), `dues-by-unit-007 as_of_change_refetches_dues` + `my-account-008 as_of_change_refetches_account` (nav step added; assertions verbatim) |
| Routing seam (one screen mounted) | `Nav.test.tsx › nav_swaps_single_screen` |
| Role seam (role from auth only) | `Role.test.tsx › *` |
| Theme seam (single source, persisted to localStorage) | `Theme.test.tsx › *` |
| Contrast (both themes) & reduced-motion | **manual** `/build` acceptance — not automatable in jsdom (see Standards-creep check) |

---

## Adversarial gate
Mode: independent clean-context sub-agent (general-purpose), run once against the
drafted spec + tests. It returned 2 HIGH, 4 MEDIUM, 2 LOW; cleared scope-drift,
behavior-sneak, role-gating framing, and the `@scaffolding` tags. **All 8 findings
were dispositioned `fixed`** (owner-confirmed the as-of model for the first HIGH); none
were acknowledged, so no rows are added to constitution.md § Acknowledged risks. No
HIGH/MEDIUM **security** finding was fixed, so no security re-gate was required.

| # | Sev | Lens | Finding | Disposition |
|---|-----|------|---------|-------------|
| 1 | HIGH | Integrity / safety-net | Dues & My account share the Dashboard's single `as_of`; making them separate nav screens breaks 3 prior refetch-coupling tests beyond a "nav step." | **Fixed** — owner chose a single app-level **shared As-of in the shell** (§ Design → Shared "As of"); the 3 tests keep assertions verbatim and gain only a nav step. |
| 2 | HIGH | Integrity / safety-net | Nav-step assertions in prior suites could collide with shell/other controls (unscoped `/save/i` etc.). | **Fixed** — single-screen mount mitigates; added contract rules: shell control names must not match write-action patterns, and added assertions are scoped to the active region. |
| 3 | MED | Coverage / Integrity | Contract omitted the "no write control inside read regions" invariant and the as-of sharing. | **Fixed** — both added to the Preservation contract. |
| 4 | MED | Integrity / safety-net | Units anchor placement loose; "101" could be ambiguous. | **Fixed** — contract: units on default Overview, no nav, unique-or-scoped. |
| 5 | MED | Coverage / Failure modes | `no_matchmedia_defaults_light` might not exercise the no-matchMedia path. | **Fixed** — test now asserts `window.matchMedia` is undefined before render. |
| 6 | MED | Coverage / Failure modes | `persists_across_remount` could pass against an in-memory store. | **Fixed** — test now asserts the preference is written to `localStorage`. |
| 7 | LOW | Integrity | `rootIsDark` accepts `data-theme` while Tailwind is `darkMode:"class"`; dark styling could silently not activate. | **Fixed** — spec § Tokens requires the root indicator to match `tailwind.config`'s `darkMode`. |
| 8 | LOW | Standards | Contrast + reduced-motion claimed but untestable in jsdom. | **Fixed** — moved to explicit **manual** `/build` acceptance in § Standards-creep + Coverage, so the gap is honest. |
