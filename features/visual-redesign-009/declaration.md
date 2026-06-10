# Feature declaration — Visual redesign (009)

## What
A cross-cutting visual redesign of the entire DWCOA Financials frontend: re-skin
every existing authenticated screen and the login screen to a modern-fintech look
(Mercury/Ramp-inspired, evergreen brand), in both light and dark mode, for both
roles. The monolithic `frontend/src/App.tsx` is decomposed into a small set of
reusable design primitives plus per-screen components, and the all-sections-on-one-
page layout becomes a **sidebar-driven, nav-switched single-page app** (one screen
shown at a time). This is purely a presentation-layer change: **no API call, no
financial calculation, no data shape, and no role/authorization behavior changes.**
The design reference in `frontend/design/` is the look-and-feel source of truth;
its specifics are secondary to what the app actually needs to keep working.

## Why
The app is fully functional but visually bare — raw HTML tables and default form
controls with zero styling (`App.tsx` has no `className` at all). The board and
homeowners open this to understand the association's money; a trustworthy, legible,
information-dense interface is part of that trust. The redesign also pays down the
1,335-line single-component monolith into primitives and screen components, which
makes every future slice cheaper to build and keeps dark mode — a first-class
surface per the constitution — consistent across screens.

## Success
- Every existing screen (Login, Overview/Dashboard, Transactions, Dues by unit,
  Budget, My account, Review queue, Rules, Import CSV) renders in the new visual
  language, light and dark, with the brand, typography, spacing, and component
  treatments from the design tokens.
- A **persisted theme toggle** switches light/dark; first visit defaults to the OS
  `prefers-color-scheme`; the choice survives reload.
- The app shell is a fixed sidebar + content area with nav that **swaps the visible
  screen**; the sidebar collapses to a drawer on narrow viewports.
- **Role is read only from `/api/auth/me`** and drives which nav items and controls
  appear; there is no user-facing role switch anywhere (the prototype's role
  segmented control is dropped). Viewers never see admin controls or admin-only nav.
- **Every behavior the 8 prior feature suites assert still holds** — same API calls,
  same money formatting (integer cents → USD via `centsToUsd`), same proration
  markers, same pagination, same `dues_tracked` pre-2025 notes, same per-unit
  selection persisted to `localStorage`. The redesign preserves the accessible
  names, roles, labels, and test-ids those suites depend on; where a screen moves
  behind navigation, the suite gains a navigation step and nothing else.
- Meets WCAG 2.1 AA contrast for text and meaningful UI in both themes.

## Shape touched
- **Dashboard & reporting UI** — the whole frontend: app shell (sidebar, topbar,
  theme toggle, nav-switched routing), shared primitives (Card, StatCard, Badge,
  Table, Button, Meter, Ring, BarChart, StackBar, Toast, Modal), and the per-screen
  components that consume the existing hooks/fetch logic unchanged.

## Out of scope
- **Any backend / API change.** No new endpoints, no payload changes, no auth
  changes. If a screen needs a value the API doesn't already return, it is not added
  here.
- **Any change to financial logic** — proration, cents↔dollars, dues math,
  transfers-excluded totals, ownership conversions. These are reused exactly.
- **Accent-color and row-density preferences** (prototype tweaks) — only light/dark
  theme ships. Evergreen is the only brand.
- **Print-clean layout and PDF export.** Already cut at the project level (see
  decision log); this feature does not add or restore them.
- **New product features or screens** — no new functionality, only re-skinning what
  exists. The prototype's "Active toggle" on rules is visual-only unless the API
  already supports it (it does not, so it stays visual or is omitted).
- **Mobile-native / responsive beyond the existing breakpoints' intent** — the SPA
  stays responsive (sidebar → drawer, grids reflow) but no native app.
- **Migrating to a component library** — custom primitives on Tailwind + CSS
  variables; not shadcn/ui (recorded deviation).
