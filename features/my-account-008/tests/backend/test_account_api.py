# @frozen for the API contract (path, top-level keys, current_year keys, status
# codes, not-tracked shape) — the surface the frontend binds to. The dues MATH is
# covered in test_account_engine.py / test_account_guidance.py; this file covers the
# HTTP edges: auth, validation, read-only, and the pre-2025 not-tracked gate.
"""US1/US6 — the /api/account endpoint surface."""
from datetime import date

from conftest import (
    SEEDED_UNITS,
    clear_budgets,
    get_account,
    insert_budget,
    table_counts,
)

TOP_LEVEL_KEYS = {
    "unit", "ownership_per_mille", "as_of_date", "year", "dues_tracked",
    "current_year", "prior_year", "payment_guidance", "recent_payments",
}
CURRENT_YEAR_KEYS = {
    "year", "carryover", "annual_dues", "total_due", "paid_ytd",
    "remaining_balance",
}


# --- payload shape (AC1.1, AC2.1) ------------------------------------------

def test_payload_has_all_keys(app_env, viewer_client):
    db = app_env["db_path"]
    clear_budgets(db, 2026)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    data = get_account(viewer_client, unit="101", as_of="2026-06-30")
    assert set(data.keys()) >= TOP_LEVEL_KEYS
    assert data["unit"] == "101"
    assert data["ownership_per_mille"] == 117
    assert data["dues_tracked"] is True


def test_year_follows_as_of(app_env, viewer_client):
    data = get_account(viewer_client, unit="101", as_of="2026-09-01")
    assert data["year"] == 2026
    assert data["as_of_date"] == "2026-09-01"
    assert data["current_year"]["year"] == 2026


def test_current_year_shape(app_env, viewer_client):
    db = app_env["db_path"]
    clear_budgets(db, 2026)
    insert_budget(db, year=2026, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    cy = get_account(viewer_client, unit="101", as_of="2026-06-30")["current_year"]
    assert set(cy.keys()) >= CURRENT_YEAR_KEYS
    for k in ("carryover", "annual_dues", "total_due", "paid_ytd",
              "remaining_balance"):
        assert isinstance(cy[k], int), k


# --- auth (AC1.2, AC1.5) ----------------------------------------------------

def test_requires_auth(client):
    """An unauthenticated request is rejected 401."""
    res = client.get("/api/account?unit=101")
    assert res.status_code == 401


def test_both_roles_can_read(admin_client, viewer_client):
    """Both admin and view-only sessions read the statement (role server-side; both
    pass)."""
    assert admin_client.get("/api/account?unit=101").status_code == 200
    assert viewer_client.get("/api/account?unit=101").status_code == 200


def test_unit_selection_is_not_authz_boundary(viewer_client):
    """A view-only session may read ANY unit (selection is a convenience, not an
    authorization boundary — declaration)."""
    for number in ("101", "202", "303"):
        data = get_account(viewer_client, unit=number)
        assert data["unit"] == number


def test_read_only_writes_nothing(app_env, viewer_client):
    """A GET mutates no table."""
    db = app_env["db_path"]
    before = table_counts(db)
    get_account(viewer_client, unit="101", as_of="2026-06-30")
    assert table_counts(db) == before


# --- validation (AC1.3, AC1.4) ----------------------------------------------

def test_omitted_as_of_defaults_today(viewer_client):
    """Absent as_of -> today's date (and its year)."""
    data = get_account(viewer_client, unit="101")          # no as_of
    today = date.today()
    assert data["as_of_date"] == today.isoformat()
    assert data["year"] == today.year


def test_malformed_as_of_400(viewer_client):
    """A non-YYYY-MM-DD as_of is a 400 (manual edge-validation, not 422)."""
    for bad in ("2026-13-01", "06/30/2026", "yesterday", "2026-6-30"):
        res = viewer_client.get(f"/api/account?unit=101&as_of={bad}")
        assert res.status_code == 400, bad


def test_missing_unit_400(viewer_client):
    """unit is required; absent -> 400."""
    assert viewer_client.get("/api/account").status_code == 400
    assert viewer_client.get("/api/account?as_of=2026-06-30").status_code == 400


def test_unknown_unit_400(viewer_client):
    """A unit not among the seeded nine -> 400."""
    assert viewer_client.get("/api/account?unit=999").status_code == 400


def test_unit_sql_injection_safe(app_env, viewer_client):
    """A malicious unit value is rejected as unknown (400) and mutates nothing —
    the value is parameterized, never interpolated."""
    db = app_env["db_path"]
    before = table_counts(db)
    res = viewer_client.get("/api/account?unit=101'; DROP TABLE units;--")
    assert res.status_code == 400
    after = table_counts(db)
    assert after == before
    assert after["units"] == len(SEEDED_UNITS)


# --- pre-2025 not tracked (AC6.*) ------------------------------------------

def test_pre_2025_not_tracked(viewer_client):
    """A pre-2025 as_of reports not-tracked with null/empty members, HTTP 200 (so an
    early date on the shared dashboard control doesn't break the section)."""
    data = get_account(viewer_client, unit="101", as_of="2024-06-30")
    assert data["dues_tracked"] is False
    assert data["current_year"] is None
    assert data["prior_year"] is None
    assert data["payment_guidance"] is None
    assert data["recent_payments"] == []


def test_2025_is_tracked(app_env, viewer_client):
    data = get_account(viewer_client, unit="101", as_of="2025-06-30")
    assert data["dues_tracked"] is True
    assert data["current_year"] is not None
