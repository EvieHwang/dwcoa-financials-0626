# Feature Declaration: Rules Categorization

**Feature:** rules-categorization-004
**Slice:** 4 of the DWCOA Financials rebuild

## What
The deterministic, rules-only categorization layer that turns the raw transaction
store (slice 3) into *categorized* data. It has four parts that form one loop:

1. **A categorization engine** — a pure, testable matcher that assigns a category
   to a transaction by the first active rule that matches it (case-insensitive
   description substring, optionally narrowed by account and amount), in a
   well-defined priority order. No match → the transaction is flagged for review.
2. **Categorize-on-ingest** — the CSV upload path (slice 3) now runs each *newly
   inserted* row through the engine, so an upload reports not just "added" but
   "categorized vs. needs review," and the engine's verdict is persisted.
3. **A review queue** — the admin sees the transactions the engine couldn't place
   (with a count badge) and fixes each one: pick a category and **Save** (a manual,
   sticky categorization), or pick a category and **Create rule** from a
   smart-stripped, editable suggested pattern so the fix generalizes.
4. **A rules editor** — full CRUD over rules (pattern, target category, optional
   account/amount conditions, priority, active). Saving a new or edited rule
   **re-runs the engine over the app's still-open transactions** (uncategorized,
   flagged-for-review, and previously rule-assigned), so a rule reaches the data
   already in the store — never overwriting a categorization a human made by hand.

No LLM is involved anywhere (constitution: rules-only categorization).

## Why
Categorization is the treasurer's single most repetitive task, and every
downstream number — budget-vs-actual, income/expense summaries, transfers-excluded
totals, dues — is only as trustworthy as the category on each transaction. The
legacy app proved the shape (substring rules + a review queue + learn-a-rule-on-
fix); this slice rebuilds it deterministically on the new store, and adapts the
one assumption the rebuild broke: because ingestion is now *idempotent
full-history re-upload* (slice 3 dedups already-stored rows), the legacy "the next
upload will catch it" loop is dead — a freshly created rule would never re-touch
rows already in the DB. So saving a rule must actively re-categorize the open
transactions, while treating a human's manual categorization (and all migrated
historical categorizations) as frozen ground truth that a rule may never clobber.

## Success
- Uploading a CSV now categorizes each new row by the active rules and reports how
  many were categorized vs. how many need review; a matched row carries its
  category, an unmatched row is flagged for review. Re-uploading changes nothing
  about rows already stored.
- The admin opens a review queue showing exactly the flagged transactions (with a
  live count), and can clear one either by saving a category directly or by
  creating a rule from a suggested, editable pattern — after which the queue
  reflects the change without a re-upload.
- Creating or editing a rule re-categorizes the app's open transactions
  (uncategorized + flagged + previously auto-assigned) immediately; a transaction
  a human categorized by hand, and every transaction categorized in the migrated
  production history, is never altered by a rule.
- The admin can view, add, edit, enable/disable, and delete rules, including
  optional account and amount-range conditions; deleting a rule never retroactively
  un-categorizes existing transactions.
- Internal transfers are categorized by an ordinary high-priority rule (seeded on a
  fresh DB, added by migration to an existing one) — there is no special-case
  transfer code in the engine.
- Only the admin can mutate rules or categorize a transaction; reads follow the
  existing auth rules; all mutations are same-origin-guarded.

## Shape touched
- **Categorization engine** — the new pure matcher, the priority/condition rules,
  the suggested-pattern heuristic, and the re-categorization sweep.
- **Transaction ingestion & store** — the upload path gains a categorize step on
  insert; a schema migration adds rule-condition columns and a per-transaction
  marker distinguishing human-set from rule-set categories; the seeded base rule
  set gains the transfer rule.
- **API layer** — rules CRUD endpoints, a single-transaction categorize endpoint,
  a suggested-pattern endpoint, and a `needs_review` filter on the existing
  transactions list, all reusing foundation's auth/CSRF guards.
- **Dashboard & reporting UI** — an admin review queue (with count badge and
  fix/create-rule actions) and an admin rules editor, added to the existing
  dashboard shell beside the upload control.

## Out of scope
- **Any LLM / AI categorization** (constitution: rules-only). The "learning" loop
  is rule-suggestion-on-fix, nothing more.
- **A separate manual "re-categorize everything" button.** Re-categorization is
  triggered by saving a rule (the owner's chosen model); there is no standalone
  bulk re-run endpoint or destructive "recategorize all, including manual" mode.
- **Retroactively re-categorizing the migrated history.** Transactions that arrived
  already-*categorized* from the production migration are treated as frozen: they
  are not swept by rule edits and never silently rewritten. Transactions that
  arrived *uncategorized* **are** flagged into the review queue on migration so the
  treasurer can clean the backlog (the queue may start large on first launch).
- **Budget, dues, transfers-excluded reporting, charts, PDF** — slices 5–8. This
  slice only assigns categories; it does not sum or report on them.
- **Editing/deleting transactions** (amounts, dates) or bulk category edits beyond
  the single-transaction review fix.
- **Regex / multi-pattern rules.** Matching stays case-insensitive substring on the
  description, optionally narrowed by account and amount range (the owner's chosen
  rule surface) — no regex, no boolean pattern composition.
