# Handoff: DWCOA Financials — Visual Redesign

## Overview
This is a full visual redesign of the **DWCOA Financials** app — the financial dashboard for the Denny Way Condo Owners Association (9 units). The current app (`frontend/src/App.tsx`) is fully functional but unstyled: bare HTML tables, default form controls, no layout. This package delivers a **modern-fintech design** (Mercury/Ramp-inspired) covering every existing screen, in both light and dark mode, for both roles (admin/treasurer + viewer/homeowner).

The goal of the handoff: **re-skin the existing app to match these mockups without changing its behavior, data flow, or API contracts.** Every screen here maps 1:1 to a component that already exists in `App.tsx`.

---

## About the Design Files
The files in this bundle are **design references created in HTML/React+Babel** — a clickable prototype showing the intended look and behavior. They are **not** production code to copy directly.

- The prototype uses **plain dollars** in mock data and **vanilla CSS** with custom properties.
- The live app uses **React + TypeScript + Vite + Tailwind**, integer **cents** at the API boundary, and real `fetch` calls.

Your task is to **recreate the look of these mockups inside the existing `frontend/` codebase**, using its real data (the API endpoints already wired in `App.tsx`), its types, and Tailwind. Keep all existing logic — auth, fetches, proration, cents↔dollars conversion, pagination, role gating — and replace only the markup/styling.

Recommended approach: introduce a small set of design tokens (Tailwind theme extension + CSS variables for light/dark), build a handful of primitives (Card, StatCard, Badge, Meter, Table, Button, Ring, BarChart), then refactor each section of `App.tsx` into styled components that consume the **same hooks/fetches that already exist**.

---

## Fidelity
**High-fidelity (hifi).** Exact colors, typography, spacing, radii, and interactions are specified below and visible in the prototype. Recreate pixel-faithfully using Tailwind + the tokens listed. Where the prototype and the live data shapes differ, **the live data shapes win** — see "Data Mapping" so figures stay correct (cents, proration, etc.).

---

## Tech Stack (target — already in repo)
- React 18 + TypeScript, Vite, Tailwind (`frontend/tailwind.config.js`, `frontend/src/index.css`).
- Backend FastAPI serves the built SPA; API under `/api/*`, session via HttpOnly cookie. **No API changes needed.**
- Fonts: prototype uses **Schibsted Grotesk** (UI) + **JetBrains Mono** (account numbers, patterns, monospace figures). Add via `@fontsource` or a `<link>`; both are on Google Fonts. If you'd rather not add fonts, the design degrades gracefully to the system sans stack, but Schibsted Grotesk is the intended look.

---

## Design Tokens

### Color — Light (default)
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F4F6F3` | App background (with a faint radial green tint top-right) |
| `--surface` | `#FFFFFF` | Cards, table backgrounds |
| `--surface-2` | `#FAFBF9` | Row hover, subtle panels |
| `--surface-3` | `#F2F4F0` | Inset chips, segmented control track, meter track |
| `--inset` | `#F6F8F4` | Inset highlight blocks (e.g. remaining balance) |
| `--ink` | `#14201B` | Primary text |
| `--ink-2` | `#586660` | Secondary text |
| `--ink-3` | `#8A958F` | Tertiary / muted / icons |
| `--border` | `#E6E9E3` | Card borders, table header rule |
| `--border-2` | `#DBDFD8` | Input borders |
| `--hairline` | `#EDEFEA` | Row dividers, internal separators |

### Color — Dark
| Token | Hex |
|---|---|
| `--bg` | `#0A0F0C` (radial green glow top-right) |
| `--surface` | `#111814` |
| `--surface-2` | `#0E1410` |
| `--surface-3` | `#161E18` |
| `--inset` | `#0C120E` |
| `--ink` | `#ECF1ED` |
| `--ink-2` | `#9AA8A0` |
| `--ink-3` | `#687670` |
| `--border` | `#232C26` |
| `--border-2` | `#2C3730` |
| `--hairline` | `#1C241F` |

### Brand (evergreen) + accents
Brand is themeable; **Evergreen is the default**. Light / Dark variants:
| Token | Light | Dark |
|---|---|---|
| `--brand` | `#0F6E45` | `#34A772` |
| `--brand-ink` (text on soft / hover) | `#0C402B` | `#6FBE96` |
| `--brand-soft` (tint bg) | `#E7F2EB` | `#16271E` |
| `--on-brand` (text on solid brand) | `#FFFFFF` | `#06140D` |

Semantic (light → dark):
| Token | Light | Dark |
|---|---|---|
| `--pos` (positive/income/paid) | `#168A57` | `#3BB57C` |
| `--pos-soft` | `#E4F3EA` | `#14271C` |
| `--neg` (negative/expense/overdue) | `#C8453B` | `#E0685C` |
| `--neg-soft` | `#FBEAE7` | `#2A1714` |
| `--amber` (needs review / behind / over pace) | `#B7791F` | `#D9A441` |
| `--amber-soft` | `#FBF0DB` | `#281E0F` |
| `--info` (reserve / credit) | `#3B6E9C` | `#6BA3D0` |
| `--info-soft` | `#E8F0F7` | `#121E29` |

Alternate accents offered as a tweak (optional to port): Indigo `#2A5BD7`, Teal `#0E7C86`, Plum `#7A4FD0`.

### Typography
- **Family:** `'Schibsted Grotesk'` (UI), `'JetBrains Mono'` (mono: account numbers `••4021`, rule patterns, dates in dense tables, optional figures).
- **Always use `font-variant-numeric: tabular-nums` on any money/number** so columns align. (Utility `.tnum`.)
- Scale (px / weight / tracking):
  - Page title: 18 / 700 / -0.02em
  - Page subtitle: 12.5 / 500 / — , color `--ink-2`
  - KPI value (big): 38 / 700 / -0.025em ; standard stat value: 30 / 700
  - Card title (`h3`): 14 / 700 / -0.01em
  - Section label (uppercase): 11–13 / 700 / +0.05em, color `--ink-3`
  - Table header: 11 / 700 / +0.05em / uppercase / `--ink-3`
  - Table cell: 13 / 400–600
  - Body/labels: 13–13.5 ; small meta: 12–12.5 ; micro: 11–11.5
  - Badge text: 11.5 / 600

### Spacing / Radius / Shadow
- Spacing base 4px. Card padding 22px (head 18×22). Content padding 24×28 desktop, 18×16 mobile. Grid gaps 16–18px.
- Radius: cards `16px`, controls/inputs/buttons `10px`, small chips `8px`, pills/badges `999px`.
- Row height (table): comfortable `44px` (compact `38`, spacious `52`) — driven by a density tweak.
- Shadows (light): card `0 1px 2px rgba(20,32,27,.05), 0 1px 1px rgba(20,32,27,.04)`; elevated `0 2px 4px /.04 + 0 8px 24px /.06`; modal `0 24px 60px -20px rgba(12,40,27,.28) …`. Dark mode leans on borders, shadows are near-black.
- Focus ring: `0 0 0 3px rgba(15,110,69,.16)` (brand at low alpha; recolor with accent).

---

## Global Layout / App Shell
A two-column app frame: **fixed 256px sidebar** + fluid main. Collapses to a slide-in drawer under 880px (hamburger appears in the topbar).

- **Sidebar** (`--surface`, right border `--border`, sticky full height, 18×14 padding):
  - Brand block: 34px rounded-9px gradient mark (evergreen `#168A57→#0C402B`, building icon, white) + "DWCOA" (15/700) over "Financials" (11/`--ink-3`).
  - Grouped nav. Group label = uppercase 10.5/700/+0.09em `--ink-3`. Nav item = 9×10 padding, radius 10, 11px gap icon(18px)+label(13.5/500 `--ink-2`). Hover: bg `--surface-3`, text `--ink`. **Active: bg `--brand-soft`, text `--brand-ink`, weight 600.** Review queue item shows an amber count pill (`--amber-soft`/`--amber`, tabular).
  - Footer: user chip (30px gradient avatar with initials "TR"/"HO", name + role, logout icon). Clicking logs out.
- **Topbar** (sticky, translucent `color-mix(--bg 78%)` + `backdrop-filter: blur(14px)`, bottom border `--border`, 14×28 padding): page title + subtitle on the left; right cluster = an "As of <date>" neutral badge, a **role segmented control** (Treasurer / Homeowner — this is a prototype affordance; see note), and a **theme toggle icon button** (moon/sun).
- **Content**: max-width 1280px (1480 "wide" for tables), centered, 24×28 padding, vertical stack gap 16–18px.

> **Role switch note:** in the prototype, the topbar Treasurer/Homeowner segmented control swaps roles live for demo purposes. In the real app the role comes from `/api/auth/me` and must NOT be user-switchable — **drop that control** (or gate it to dev only). Keep the theme toggle.

---

## Screens / Views
Each maps to an existing function in `App.tsx`.

### 1. Login  → `Login`
Two-panel, full viewport.
- **Left brand panel** (~52%): diagonal evergreen gradient `#0D5638→#0A2B1E` with a soft radial highlight; white text. Top: brand mark + "DWCOA Financials" / "Denny Way Condo Owners Association". Middle: headline 32/700/-0.03em "Every dollar across nine homes, in one clear ledger." + a row of three stats ($177k Total cash · 9 Units · 96% Dues collected). Bottom: faint "Board-only access · Seattle, WA".
- **Right form panel** (~48%, centered, max-width 340): "Welcome back" (23/700) + subtitle; **a "Sign in as" segmented control (Treasurer/Homeowner) — prototype only; in production the password determines the role** (admin vs board password, per backend). Password input; primary full-width "Log in" button (42px) with arrow icon; error text in `--neg` on empty/incorrect.
- Real behavior already in `App.tsx`: POST `/api/auth/login` `{ password }`; on 200 refresh auth; 429 → rate-limit message; else "Incorrect password." Keep exactly. Under 720px, stack to single column (hide or shrink the brand panel).

### 2. Overview  → `Dashboard` (+ `SummaryTable`, reserve, cashflow)
Vertical stack:
1. **KPI row** — 4 `StatCard`s (grid, responsive 4→2→1):
   - Total cash on hand (big) — `total_cash`, delta vs sum of `accounts[].beginning_balance`. Icon wallet/brand.
   - Reserve fund — `reserve_fund` current vs `beginning_balance` delta; sub "% of total cash". Icon bank/info.
   - Net income YTD — `income_summary.actual − expense_summary.actual`; sub = two badges (income in / expense out). Icon trend.
   - Dues collected YTD — `dues.totals.paid`; sub "% of expected · N units behind". Icon coins.
2. **Cash flow + Reserve** (grid `1.9fr 1fr`):
   - **Cash flow card**: grouped vertical bar chart of `monthly_cashflow` (income = brand bar, expense = `--ink-3` bar at ~55% opacity), 12 months, y-grid with compact `$k` labels, hover tooltip (month, income, expense). Legend in header.
   - **Reserve fund card**: a **progress Ring** (donut) = contributions / annual reserve plan, center shows %; below, three rows Contributed / Reserve spend (neg) / Net to reserve (bold).
3. **Budget vs actual** (grid 2-col): two cards, **Income** and **Operating expenses**, each = `SummaryTable` data rendered as category rows with a **Meter** (actual / annual_budget). Header sub = "<actual> of <annual> annual · N%". Each row: icon + name (left), `actual / annual` (right, actual bold), meter, and a thin **pace marker** at `prorated_budget / annual_budget` (a 2px vertical tick in `--ink-3`). **Expenses** flag "over pace" (amber badge + amber meter) when `actual > prorated_budget × 1.08`; **income does NOT show over-pace.**
4. **Accounts + Dues snapshot** (grid 2-col):
   - **Account balances** table: per account icon + name + masked number, Beginning, Current (bold), Change (signed, pos/neg color); total row. "View transactions →" in header navigates to Transactions.
   - **Dues collection** card: big collected figure + collected-% badge; a **StackBar** (paid = brand, outstanding = amber); legend; divider; up to 3 behind-units with amount due, or "All units current" with check.

   Data: `GET /api/dashboard?as_of=<date>` and `GET /api/dues?as_of=<date>` (both already fetched). Render-only; no writes.

### 3. Transactions  → the Transactions section of `DashboardShell`
Single card. Header: title + actions (search input with leading icon, Year select, Account select, Export button — Export can be a no-op/stub if not implemented). Table columns: Date (mono-ish muted), Account (masked `••4021` mono), Description (500), **Category** (neutral badge, or amber "Needs review" badge when null), Debit (neg color), Credit (pos color), Balance (muted). Footer: "Showing X–Y of N" + prev/next icon buttons.
- Behavior already present: `GET /api/transactions?limit&offset&year&account`; pagination via offset; filters reset offset to 0. Keep. (Prototype paginates client-side over mock rows; live keeps server pagination.)

### 4. Dues by unit  → `DuesByUnit`
Three `StatCard`s (Expected to date / Collected / Outstanding) then a table: Unit (bold), Ownership %, Monthly, Carryover (neg shown red if owed, green if credit), Expected, Paid, Outstanding (bold, red if >0), **Status** badge (Current = green, Behind = amber, Credit = info). Totals row. Data: `GET /api/dues?as_of`. If `dues_tracked === false` (pre-2025), show the existing "tracking begins 2025" note instead of rows.

### 5. Budget  → `BudgetEditor`
Three `StatCard`s (Budgeted income / Budgeted expense / Planned surplus, recomputed live from edits). Card header: "Annual budget" + Year select + a "Locked" badge when locked. **Admin-only action cluster:** Copy `<year-1>` (opens a confirm modal → overwrite), Lock/Unlock year, Save changes (enabled only when dirty & unlocked). Table: Category (icon+name), Type badge (Income green / Expense neutral), Timing (muted), Annual budget (bold), and **admin-only** Edit (USD) — a number input with a leading `$`, disabled when locked. Net operating budget total row.
- Real behavior in `App.tsx`: `GET /api/budgets?year`; Save = per-edited-line POST `/api/budgets` with **integer cents** (`Math.round(dollars*100)`); Copy = POST `/api/budgets/copy` (on 409 → confirm → retry `overwrite:true`); Lock = POST `/api/budgets/lock`. **Viewer sees the table read-only — no edit column, no action cluster.** Keep all of this; only restyle.

### 6. My account  → `MyAccount`
Header card: avatar + "Unit <n> statement" + "X% ownership · as of <date>" + a unit `<select>` (persisted to `localStorage` key `dwcoa.my-account.unit`). Grid 2-col:
- **This year (year)** card: rows Balance carried over / Annual dues / Total due (bold) / Paid YTD (neg, green), then an inset highlight block "Remaining balance" (22/700, amber if owing, pos if ≤0). Status badge in header (Balance due / Paid in full / Credit).
- Right column: **Payment guidance** card (Standard monthly; if `status==='owes'` show suggested monthly to stay current in a brand-soft block, else a positive "paid in full"/"credit" note; "N months remaining") + **Recent payments** card (check icon + date + +amount).
- Data: `GET /api/account?unit=<n>&as_of=<date>`. If `dues_tracked===false`, show the existing pre-2025 note. Read-only.

### 7. Review queue  (admin) → `review-queue` section
Three `StatCard`s (Awaiting review = count / Active rules / Auto-matched %). Card with a table: Date, Description, Amount (neg if debit else pos), **Category select**, Actions = **Save** (primary) + **Rule** (opens Create-rule modal). Saving removes the row and toasts. Empty state: "Inbox zero — every transaction is categorized."
- Real behavior: queue = `GET /api/transactions?needs_review=true`; Save = `PATCH /api/transactions/:id { category_id }`; "Create rule" pre-fills a pattern via `GET /api/rules/suggest?description=…`. Keep; restyle. Count drives the **sidebar badge**.

### 8. Categorization rules  (admin) → `rules-editor` section
"New rule" card: pattern input (mono) + category select + Add button. "Categorization rules" table: Pattern (mono), Category (brand badge), Conditions (account/min/max or "—"), Priority, **Active toggle** (custom switch), Delete (danger icon button). Inactive rows at ~55% opacity.
- Real behavior: `GET /api/rules`; create = POST `/api/rules { pattern, category_id }`; delete = DELETE `/api/rules/:id`. (Active toggle is a UI affordance in the prototype — wire to a PATCH only if the API supports it; otherwise keep visual only or omit.)

### 9. Import CSV  (admin) → Upload section
Card with a **drag-and-drop zone** (dashed border, upload icon in a raised tile, "Drop your CSV here or click to browse", accepts `.csv`). After upload, a **summary panel**: green "Import complete — N rows read" header + a 3-up grid (Added / Duplicates skipped / Unknown account) + a note listing unmatched account numbers.
- Real behavior: POST `/api/transactions/upload` (multipart `file`); response `{ added, skipped_duplicate, unknown_account_count, unknown_accounts[], total }`; on success reset offset + reload table. Keep; restyle. Surface server `detail` errors in a `--neg` alert.

---

## Interactions & Behavior
- **Routing:** single-page, section state (`page`) swaps the content region; nav + sidebar badge reflect it. (Prototype uses local state; in the app you can keep `App.tsx`'s structure or introduce a router — your call, behavior unchanged.)
- **Theme:** `data-theme="light|dark"` on `<html>` swaps the token blocks; theme toggle in topbar. Persist preference (prototype stores it via the tweak layer; in the app use `localStorage` + `prefers-color-scheme` default).
- **Hover:** rows → `--surface-2`; buttons → darker surface/border; nav → `--surface-3`. ~120–140ms transitions.
- **Meters/Ring:** animate width / stroke-dashoffset on value change (~.6–1s ease-out). **Important:** resting state must be the *visible* end state — do not gate visibility on entrance animations (a paused animation must still show full content). Avoid `opacity:0` "fade-up" entrances on always-on content.
- **Toasts:** bottom-center, dark pill with a brand-tint icon, auto-dismiss ~2.6s, used after Save / Lock / Copy / rule create-delete / import.
- **Modals:** scrim `rgba(8,16,12,.5)` + slight blur; centered card max-width 440; used for Copy-year confirm and Create-rule.
- **Reduced motion:** respect `prefers-reduced-motion` (disable animations).
- **Responsive:** KPI 4→2→1; 2-col grids → 1-col under ~1100/880px; sidebar → drawer under 880px; content padding shrinks. Min tap target 44px on mobile.

## State Management
Keep what `App.tsx` already has — don't re-architect:
- Auth: `{status:'loading'|'unauthenticated'|'authenticated', role}` from `/api/auth/me`.
- Reference data (`/api/reference`): units, accounts, categories.
- Per-section fetch state with reload tokens (transactions, review queue, rules, budget, dashboard, dues, account).
- Local UI: current `page`, theme, density, nav-drawer open, edit buffers (budget), review category selections, toast list, modal open flags.
- New (UI-only): `theme`, `accent`, `density` preferences.

## Data Mapping (don't break the numbers)
- **Money is integer cents in the API.** Keep `centsToUsd` (`cents/100` → `toLocaleString` USD). The prototype's dollar values are illustrative only.
- **Proration** is backend-computed (`prorated_budget`); the pace marker = `prorated_budget / annual_budget`. Don't recompute on the client.
- **Ownership**: dashboard units use `ownership_pct` (×100 for %); dues use `ownership_per_mille` (÷10 for %). Mind which endpoint you're reading.
- **Dues `dues_tracked` flag** gates the pre-2025 note on Dues and My Account.
- **Role gating**: admin-only = Upload, Review queue, Rules, Budget edit controls. Viewer = read-only everywhere. Source of truth is `role` from auth, not a UI switch.

## Assets
- **Icons:** a custom line-icon set (Feather/Lucide style, 1.9px stroke) is in `icons.jsx`. Easiest path in the real app: use **lucide-react** — equivalents exist for all (building, wallet, bank/landmark, coins, receipt, pie-chart, user, inbox, list/rules, upload, trending-up, check-circle, alert-triangle, calendar, search, chevrons, lock/unlock, copy, trash, sun, moon, etc.). Category glyphs: umbrella (insurance), droplet (water), zap (electric), flame (gas), leaf (landscaping), sparkles (janitorial), wrench (repairs), briefcase (management), truck (trash), shield (legal), percent (interest).
- **Fonts:** Schibsted Grotesk + JetBrains Mono (Google Fonts / @fontsource).
- No raster images; the brand mark is an icon in a gradient tile.

## Files in this bundle
- `index.html` — entry; loads React 18 + Babel + the scripts below.
- `styles.css` — **design tokens** (light/dark variables, type, radii, shadows) — the source of truth for values above.
- `components.css` — component styles (sidebar, topbar, cards, tables, buttons, inputs, badges, meters, modal, toast, responsive).
- `data.jsx` — mock data + format helpers (`usd`, `pct`, `fmtDate`) and the realistic DWCOA dataset (useful as fixtures / to sanity-check shapes).
- `icons.jsx` — the icon set.
- `charts.jsx` — primitives: `Delta`, `Meter`, `Ring`, `BarChart`, `StackBar`, `Legend`, `StatCard`.
- `screens-finance.jsx` — Overview, Dues, My Account (+ `BudgetVsActual`, `CardHead`).
- `screens-admin.jsx` — Transactions, Budget, ReviewQueue, Rules, Import (incl. modals).
- `app.jsx` — shell: Login, sidebar/topbar, routing, theme + tweaks, toasts.

Open `index.html` to interact with the full prototype (any password logs in; use the topbar segmented control to preview both roles; toggle theme top-right; the Tweaks panel exposes dark mode, accent, density).

## Suggested implementation order
1. Tokens: extend Tailwind theme + add light/dark CSS variables; wire fonts; add a `tnum` utility.
2. Primitives: Button, Card, Badge, Table, StatCard, Meter, Ring, BarChart, StackBar, Toast, Modal.
3. App shell: Sidebar + Topbar + content routing + theme toggle (role from auth, not a switch).
4. Re-skin sections in place, reusing the existing fetch/handler logic from `App.tsx`, one at a time: Overview → Transactions → Dues → My account → Budget → Review → Rules → Import → Login.
5. Verify role gating, cents formatting, proration markers, and dark mode across every screen.
