# Legacy data migration — operator runbook

A one-time, **offline** cutover that moves the live production data out of the
legacy AWS-serverless app and into this app's schema. These steps only run from
a **local session with AWS access** (the cloud sandbox has neither the AWS
credentials nor the Fly volume). Run them in order; the importer itself is pure
and tested, but the S3 pull and the Fly file-landing are manual and are the
parts this runbook exists to make repeatable and auditable.

Prerequisites:

- AWS credentials for account `070840362692` (region `us-east-1`).
- `flyctl` authenticated against the DWCOA Financials Fly app.
- A checkout of this repo with the backend venv installed
  (`cd backend && python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"`).

## 1. Pull the legacy database from S3

The legacy production SQLite database lives in S3. Pull it to a local working
directory:

```bash
aws s3 cp s3://dwcoa-data-070840362692/dwcoa.db ./dwcoa-legacy.db
```

This file contains real, private financial data — keep it local, never commit
it, and delete it when the cutover is verified.

## 2. Run the importer

Transform the legacy DB into a new-schema SQLite file. The importer validates
the source's shape up front, converts money to integer cents and ownership to
integer per-mille, preserves every primary key, and writes the budget-lock
state — all inside a single all-or-nothing transaction.

```bash
cd backend
.venv/bin/python -m app.legacy_import \
    --source ../dwcoa-legacy.db \
    --target ../dwcoa-new.db
```

- The importer **refuses to overwrite** a target that already holds transaction
  data. To deliberately rebuild an existing target, add `--force`.
- Any failure (missing/unreadable source, unexpected source schema, a
  constraint violation mid-load) aborts and leaves **no partial target** — fix
  the cause and re-run. A dry-run or re-run against a fresh target path is
  always safe.

## 3. Land the file on the Fly volume

The deployed app serves a freshly-seeded skeleton DB on its mounted volume.
Replace it with the migrated file. First stop writes (the treasurer is the only
writer; coordinate the cutover so no upload is in flight), then copy the file
over using `fly ssh sftp`:

```bash
# inspect / locate the volume-mounted DB path the app uses (e.g. /data/dwcoa.db)
fly ssh console -C "ls -l /data"

# upload the migrated DB, replacing the seeded skeleton
fly ssh sftp shell
> put ../dwcoa-new.db /data/dwcoa.db
> quit
```

Restart the app so it opens the replaced file:

```bash
fly apps restart <app-name>
```

On startup the app runs migrations idempotently (a no-op on the migrated DB) and
the reference seed, which is a **true no-op** against the migrated data —
because the DB already holds categories, the seed adds no rows and changes no
values. No phantom or contradictory rows are injected.

## 4. Verify the cutover

Confirm the live app holds exactly what the legacy system held. Spot-check
counts and the lock state against the source DB:

```bash
# counts in the migrated source (run locally against dwcoa-new.db)
sqlite3 ../dwcoa-new.db "SELECT 'transactions', COUNT(*) FROM transactions
  UNION ALL SELECT 'budgets', COUNT(*) FROM budgets
  UNION ALL SELECT 'categories', COUNT(*) FROM categories
  UNION ALL SELECT 'units', COUNT(*) FROM units
  UNION ALL SELECT 'unit_past_dues', COUNT(*) FROM unit_past_dues
  UNION ALL SELECT 'categorize_rules', COUNT(*) FROM categorize_rules;"

# per-year transaction counts
sqlite3 ../dwcoa-new.db "SELECT substr(post_date,1,4) AS yr, COUNT(*)
  FROM transactions GROUP BY yr ORDER BY yr;"

# locked years — expect 2025 and 2026 locked
sqlite3 ../dwcoa-new.db "SELECT year, locked, locked_at FROM budget_locks ORDER BY year;"
```

Verification checklist — the cutover is complete only when all of these hold:

- [ ] Per-table row counts on the live app equal the legacy source.
- [ ] Per-year transaction counts match the legacy source.
- [ ] Per-year budget totals (in cents) match the legacy source to the cent.
- [ ] The locked years are preserved (currently **2025** and **2026** locked).
- [ ] The dashboard renders real balances, budgets, and per-unit dues — no
      phantom seed categories (e.g. there is `Interest`, not `Interest income`).
- [ ] The local `dwcoa-legacy.db` / `dwcoa-new.db` working copies are deleted.

## Cutover log

A dated record of each time this runbook was executed against production, for
audit and so a future operator can see when the live data last changed hands.

### 2026-06-10 — initial production cutover

First load of real production data onto the Fly volume; the app had been running
on the freshly-seeded skeleton DB until this point.

- **Source:** `s3://dwcoa-data-070840362692/dwcoa.db`, pulled locally and run
  through `python -m app.legacy_import` (source schema validated, no mismatch).
- **Landing:** uploaded via `fly ssh sftp` to `/data/dwcoa-new.db`, then swapped
  into place (`mv /data/dwcoa.db /data/dwcoa.db.bak` → `mv /data/dwcoa-new.db
  /data/dwcoa.db`) and `fly apps restart`. The prior seeded skeleton is retained
  on the volume as `/data/dwcoa.db.bak` for rollback.
- **Migrated file size:** 385,024 bytes.
- **Row counts (migrated target):**

  | table | rows |
  |---|---|
  | transactions | 1369 |
  | budgets | 46 |
  | categories | 27 |
  | units | 9 |
  | unit_past_dues | 4 |
  | categorize_rules | 30 |

- **Per-year transactions:** 2021: 172, 2022: 281, 2023: 269, 2024: 261,
  2025: 273, 2026: 113.
- **Locked years preserved:** 2025 and 2026.
- **Post-restart:** machine returned healthy (1/1); startup migrations and seed
  were no-ops against the populated DB, as designed.
