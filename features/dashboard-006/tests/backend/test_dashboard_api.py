# @frozen — the endpoint contract: GET /api/dashboard, its auth behavior, its
# as_of handling (default-today / 400-on-malformed), and the presence of the
# documented top-level sections. The aggregation function names are @scaffolding
# (tested via the endpoint, not imported), but this surface — path, status codes,
# payload sections — is what the frontend binds to and is frozen.
"""US1 / AC1.* — the dashboard read endpoint."""
from datetime import date

from conftest import (
    ADMIN_PW,
    BOARD_PW,
    do_login,
    get_dashboard,
    insert_txn,
    table_counts,
)

SECTIONS = (
    "as_of_date",
    "year",
    "accounts",
    "total_cash",
    "income_summary",
    "expense_summary",
    "reserve_fund",
    "monthly_cashflow",
)


def test_payload_has_all_sections(viewer_client):
    data = get_dashboard(viewer_client, "2030-06-30")
    for key in SECTIONS:
        assert key in data, f"missing dashboard section {key!r}"
    # The summaries carry totals + per-category lines.
    for summary in ("income_summary", "expense_summary"):
        for key in ("annual_budget", "prorated_budget", "actual", "remaining",
                    "categories"):
            assert key in data[summary], f"{summary} missing {key!r}"
    for key in ("budget", "contributions", "expenses", "net", "beginning_balance"):
        assert key in data["reserve_fund"]


def test_year_follows_as_of(viewer_client):
    assert get_dashboard(viewer_client, "2027-03-15")["year"] == 2027
    assert get_dashboard(viewer_client, "2030-12-31")["year"] == 2030


def test_requires_auth(client):
    # No login performed on the bare client.
    res = client.get("/api/dashboard?as_of=2030-06-30")
    assert res.status_code == 401


def test_both_roles_can_read(admin_client, viewer_client):
    assert admin_client.get("/api/dashboard?as_of=2030-06-30").status_code == 200
    assert viewer_client.get("/api/dashboard?as_of=2030-06-30").status_code == 200


def test_omitted_as_of_defaults_today(viewer_client):
    res = viewer_client.get("/api/dashboard")
    assert res.status_code == 200
    # Default as-of is today -> the reported year is the current calendar year.
    assert res.json()["year"] == date.today().year


def test_malformed_as_of_400(viewer_client):
    for bad in ("not-a-date", "2030-13-40", "06/30/2030", "2030-6-30-x"):
        res = viewer_client.get(f"/api/dashboard?as_of={bad}")
        assert res.status_code == 400, (bad, res.status_code)


def test_read_only_writes_nothing(app_env, admin_client):
    """AC1.4 — the GET mutates no table. The spec leans on read-only-ness to
    justify omitting the CSRF guard every write router applies, so the property
    is asserted, not assumed. Run as admin (the role that *could* write
    elsewhere)."""
    db = app_env["db_path"]
    insert_txn(db, account_name="Checking", post_date="2030-02-01",
               debit=1000, balance=5000)
    before = table_counts(db)
    assert admin_client.get("/api/dashboard?as_of=2030-06-30").status_code == 200
    assert table_counts(db) == before
