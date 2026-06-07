"""Rules router (D3): admin-only CRUD over categorize_rules, the
single-transaction suggestion endpoint, and the re-categorization sweep that
fires on a successful create/update.

Reuses foundation's `require_admin` guard, the `is_cross_origin` same-origin
(CSRF) defense, and `get_connection` (FK enforcement on). The matching and
suggestion logic live in `app.categorize`; the sweep lives in
`app.recategorize`. This module owns only the HTTP surface and validation.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from .. import auth as auth_mod
from .. import categorize, recategorize
from ..db import get_connection
from ..dependencies import require_admin

router = APIRouter(prefix="/api/rules")

_RULE_SELECT = (
    "SELECT r.id, r.pattern, r.category_id, c.name AS category, r.account, "
    "r.amount_min, r.amount_max, r.priority, r.confidence, r.active "
    "FROM categorize_rules r LEFT JOIN categories c ON r.category_id = c.id "
)


class RuleCreate(BaseModel):
    pattern: str
    category_id: int
    account: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    priority: int = 0
    confidence: int = 100
    active: bool = True


class RuleUpdate(BaseModel):
    pattern: str | None = None
    category_id: int | None = None
    account: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    priority: int | None = None
    confidence: int | None = None
    active: bool | None = None


def _reject_cross_origin(request: Request) -> None:
    if auth_mod.is_cross_origin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin request rejected",
        )


def _category_exists(con: sqlite3.Connection, category_id: int) -> bool:
    return con.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone() is not None


def _duplicate_exists(
    con: sqlite3.Connection,
    pattern: str,
    account: str | None,
    amount_min: int | None,
    amount_max: int | None,
    exclude_id: int | None = None,
) -> bool:
    """A rule collides when its trimmed pattern (case-insensitive) and all three
    conditions match another rule's (R5)."""
    sql = (
        "SELECT 1 FROM categorize_rules WHERE LOWER(pattern) = LOWER(?) "
        "AND account IS ? AND amount_min IS ? AND amount_max IS ?"
    )
    params: list = [pattern, account, amount_min, amount_max]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    return con.execute(sql, params).fetchone() is not None


def _fetch_rule(con: sqlite3.Connection, rule_id: int) -> dict | None:
    row = con.execute(_RULE_SELECT + "WHERE r.id = ?", (rule_id,)).fetchone()
    return dict(row) if row else None


@router.get("")
def list_rules(request: Request, _role: str = Depends(require_admin)):
    con = get_connection(request.app.state.config.database_path)
    try:
        rows = con.execute(
            _RULE_SELECT + "ORDER BY r.priority DESC, r.id"
        ).fetchall()
    finally:
        con.close()
    return {"rules": [dict(row) for row in rows]}


@router.get("/suggest")
def suggest(
    request: Request,
    description: str = "",
    _role: str = Depends(require_admin),
):
    return {"pattern": categorize.suggest_pattern(description)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_rule(
    request: Request,
    payload: RuleCreate,
    _role: str = Depends(require_admin),
):
    _reject_cross_origin(request)

    pattern = payload.pattern.strip()
    if not pattern:
        raise HTTPException(status_code=400, detail="Pattern must not be empty")

    con = get_connection(request.app.state.config.database_path)
    try:
        if not _category_exists(con, payload.category_id):
            raise HTTPException(status_code=400, detail="Unknown category")
        if _duplicate_exists(
            con, pattern, payload.account, payload.amount_min, payload.amount_max
        ):
            raise HTTPException(status_code=400, detail="Duplicate rule pattern")

        try:
            cur = con.execute(
                "INSERT INTO categorize_rules "
                "(pattern, category_id, account, amount_min, amount_max, "
                "priority, confidence, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pattern, payload.category_id, payload.account, payload.amount_min,
                 payload.amount_max, payload.priority, payload.confidence,
                 int(payload.active)),
            )
            rule_id = cur.lastrowid
            recategorize.sweep(con)
            con.commit()
        except Exception:
            con.rollback()
            raise
        return _fetch_rule(con, rule_id)
    finally:
        con.close()


@router.patch("/{rule_id}")
def update_rule(
    rule_id: int,
    request: Request,
    payload: RuleUpdate,
    _role: str = Depends(require_admin),
):
    _reject_cross_origin(request)

    fields = payload.model_dump(exclude_unset=True)
    con = get_connection(request.app.state.config.database_path)
    try:
        existing = con.execute(
            "SELECT pattern, category_id, account, amount_min, amount_max "
            "FROM categorize_rules WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Rule not found")

        if "pattern" in fields:
            fields["pattern"] = fields["pattern"].strip()
            if not fields["pattern"]:
                raise HTTPException(status_code=400, detail="Pattern must not be empty")
        if "category_id" in fields and not _category_exists(con, fields["category_id"]):
            raise HTTPException(status_code=400, detail="Unknown category")

        # The effective post-update identity, for the collision check (R5).
        merged = dict(existing)
        merged.update(fields)
        if _duplicate_exists(
            con, merged["pattern"], merged["account"], merged["amount_min"],
            merged["amount_max"], exclude_id=rule_id,
        ):
            raise HTTPException(status_code=400, detail="Duplicate rule pattern")

        try:
            if fields:
                sets = []
                params: list = []
                for key, value in fields.items():
                    if key == "active":
                        value = int(value)
                    sets.append(f"{key} = ?")
                    params.append(value)
                params.append(rule_id)
                con.execute(
                    f"UPDATE categorize_rules SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
            recategorize.sweep(con)
            con.commit()
        except Exception:
            con.rollback()
            raise
        return _fetch_rule(con, rule_id)
    finally:
        con.close()


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: int,
    request: Request,
    _role: str = Depends(require_admin),
):
    _reject_cross_origin(request)
    con = get_connection(request.app.state.config.database_path)
    try:
        cur = con.execute("DELETE FROM categorize_rules WHERE id = ?", (rule_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        # No sweep: deleting a rule never retroactively alters transactions (R5).
        con.commit()
    finally:
        con.close()
    return {"deleted": rule_id}
