"""Transactions router: admin-only CSV ingestion + authenticated list/filter.

Both endpoints reuse foundation patterns: `require_admin`/`require_auth` guards,
the `is_cross_origin` same-origin (CSRF) defense, and `get_connection` (FK
enforcement on). The parsing/dedup business logic lives in `app.ingest`; this
module owns only the HTTP surface, the size bound, the existing-identity DB read,
and the single atomic insert transaction (constitution: "business logic lives in
modules, not in route handlers").
"""
from __future__ import annotations

import sqlite3

from fastapi import (
    APIRouter, Depends, File, HTTPException, Request, UploadFile, status,
)
from pydantic import BaseModel

from .. import auth as auth_mod
from .. import categorize, ingest, recategorize
from ..db import get_connection
from ..dependencies import require_admin, require_auth

router = APIRouter(prefix="/api/transactions")

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 1000

# Categorization verdict columns are written alongside the row on insert (R2).
_INSERT_SQL = (
    "INSERT INTO transactions "
    "(account_number, account_name, post_date, check_number, description, "
    "debit, credit, status, balance, category_id, auto_category_id, "
    "category_source, confidence, needs_review) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


class CategorizePayload(BaseModel):
    category_id: int


def _reject_cross_origin(request: Request) -> None:
    if auth_mod.is_cross_origin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin request rejected",
        )


def _account_map(con: sqlite3.Connection) -> dict[str, str]:
    return {
        row["masked_number"]: row["name"]
        for row in con.execute("SELECT masked_number, name FROM accounts")
    }


@router.post("/upload")
async def upload_transactions(
    request: Request,
    file: UploadFile = File(...),
    _role: str = Depends(require_admin),
):
    _reject_cross_origin(request)

    max_bytes = request.app.state.config.ingest_max_upload_bytes
    # Reject an over-large upload before processing it (R10). The declared
    # Content-Length is the cheap early check; the read bound is the backstop.
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Upload exceeds the maximum allowed size",
                )
        except ValueError:
            pass

    raw = await file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Upload exceeds the maximum allowed size",
        )

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not valid UTF-8 text",
        )

    db_path = request.app.state.config.database_path
    con = get_connection(db_path)
    try:
        result = ingest.parse_csv(content, _account_map(con))

        # Any structural or row-level error rejects the whole upload (R1/R6) —
        # no writes happen before this check.
        if result.errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": result.errors},
            )

        existing = {
            ingest.dedup_key(
                row["account_number"], row["post_date"], row["description"],
                row["debit"], row["credit"], row["balance"],
            )
            for row in con.execute(
                "SELECT account_number, post_date, description, debit, credit, "
                "balance FROM transactions"
            )
        }

        # Load the active rules once and categorize each newly inserted row
        # inside the same atomic insert transaction (R2). Deduped rows are not
        # touched, so an existing row's category / source / review state survive.
        rules = recategorize.load_active_rules(con)

        added = 0
        store_skipped = 0
        categorized = 0
        needs_review_count = 0
        try:
            for row in result.rows:
                key = ingest.dedup_key(
                    row.account_number, row.post_date, row.description,
                    row.debit, row.credit, row.balance,
                )
                if key in existing:
                    store_skipped += 1
                    continue
                verdict = categorize.match(
                    row.description, row.account_name, row.debit, row.credit,
                    rules,
                )
                if verdict.needs_review:
                    cat_id = auto_id = source = conf = None
                    flagged = 1
                    needs_review_count += 1
                else:
                    cat_id = auto_id = verdict.category_id
                    source = "auto"
                    conf = verdict.confidence
                    flagged = 0
                    categorized += 1
                con.execute(
                    _INSERT_SQL,
                    (row.account_number, row.account_name, row.post_date,
                     row.check_number, row.description, row.debit, row.credit,
                     row.status, row.balance, cat_id, auto_id, source, conf,
                     flagged),
                )
                existing.add(key)
                added += 1
            con.execute(
                "INSERT INTO app_config (key, value) "
                "VALUES ('last_upload_at', datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = excluded.value, updated_at = datetime('now')"
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    finally:
        con.close()

    skipped_duplicate = result.duplicate_count + store_skipped
    return {
        "added": added,
        "skipped_duplicate": skipped_duplicate,
        "unknown_account_count": len(result.unknown_accounts),
        "unknown_accounts": result.unknown_accounts,
        "total": added + skipped_duplicate,
        # Additive categorization counts (R2); existing fields unchanged.
        "categorized": categorized,
        "needs_review": needs_review_count,
    }


@router.patch("/{txn_id}")
def categorize_transaction(
    txn_id: int,
    request: Request,
    payload: CategorizePayload,
    _role: str = Depends(require_admin),
):
    """Manually set one transaction's category (sticky): source becomes
    `manual`, `needs_review` clears, and no later rule sweep touches it (R4)."""
    _reject_cross_origin(request)

    db_path = request.app.state.config.database_path
    con = get_connection(db_path)
    try:
        if con.execute(
            "SELECT 1 FROM categories WHERE id = ?", (payload.category_id,)
        ).fetchone() is None:
            raise HTTPException(status_code=400, detail="Unknown category")
        if con.execute(
            "SELECT 1 FROM transactions WHERE id = ?", (txn_id,)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        con.execute(
            "UPDATE transactions SET category_id = ?, category_source = 'manual', "
            "needs_review = 0, updated_at = datetime('now') WHERE id = ?",
            (payload.category_id, txn_id),
        )
        con.commit()
    finally:
        con.close()
    return {"id": txn_id, "category_id": payload.category_id, "needs_review": 0}


@router.get("")
def list_transactions(
    request: Request,
    year: int | None = None,
    account: str | None = None,
    needs_review: bool | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
    _role: str = Depends(require_auth),
):
    # Bound the page so a caller can never request an unbounded result (R9).
    if limit < 1:
        limit = DEFAULT_PAGE_LIMIT
    limit = min(limit, MAX_PAGE_LIMIT)
    if offset < 0:
        offset = 0

    where: list[str] = []
    params: list = []
    if year is not None:
        where.append("t.post_date >= ? AND t.post_date < ?")
        params.extend([f"{year:04d}-01-01", f"{year + 1:04d}-01-01"])
    if account is not None:
        where.append("t.account_name = ?")
        params.append(account)
    if needs_review is not None:
        # The review-queue filter (R3): only flagged rows when true.
        where.append("t.needs_review = ?")
        params.append(1 if needs_review else 0)
    clause = (" WHERE " + " AND ".join(where)) if where else ""

    db_path = request.app.state.config.database_path
    con = get_connection(db_path)
    try:
        total = con.execute(
            f"SELECT COUNT(*) FROM transactions t{clause}", params
        ).fetchone()[0]
        rows = con.execute(
            "SELECT t.id, t.account_number, t.account_name, t.post_date, "
            "t.check_number, t.description, t.debit, t.credit, t.status, "
            "t.balance, t.needs_review, c.name AS category "
            "FROM transactions t LEFT JOIN categories c ON t.category_id = c.id"
            f"{clause} ORDER BY t.post_date DESC, t.id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    finally:
        con.close()

    return {
        "transactions": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
