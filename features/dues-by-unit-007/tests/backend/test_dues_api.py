# @frozen — the endpoint contract: path, auth, payload keys, year/as-of handling,
# the dues_tracked gate, read-only-ness, and aggregate identities. Money assertions
# are integer cents. The internal function names are not pinned here (@scaffolding);
# only observable HTTP behavior is.
"""US1 / US5 / AC2.1 / AC6.2 — the /api/dues HTTP surface."""
from datetime import date

from conftest import (
    SEEDED_UNITS,
    clear_budgets,
    get_dues,
    insert_budget,
    insert_past_due,
    insert_payment,
    table_counts,
)

UNIT_KEYS = {
    "unit", "ownership_per_mille", "carryover", "annual_dues",
    "expected_total", "paid", "outstanding",
}
TOTAL_KEYS = {"carryover", "annual_dues", "expected_total", "paid", "outstanding"}


def test_payload_has_all_keys(viewer_client):
    data = get_dues(viewer_client, "2026-06-30")
    assert set(data) >= {
        "as_of_date", "year", "dues_tracked", "operating_budget", "units", "totals",
    }
    assert data["as_of_date"] == "2026-06-30"
    assert set(data["totals"].keys()) == TOTAL_KEYS


def test_year_follows_as_of(viewer_client):
    assert get_dues(viewer_client, "2027-03-15")["year"] == 2027


def test_requires_auth(client):
    """An unauthenticated request is rejected 401 (client is not logged in)."""
    res = client.get("/api/dues?as_of=2026-06-30")
    assert res.status_code == 401


def test_omitted_as_of_defaults_today(viewer_client):
    """No as_of -> today; year is the current calendar year, not an error."""
    res = viewer_client.get("/api/dues")
    assert res.status_code == 200
    assert res.json()["year"] == date.today().year


def test_malformed_as_of_400(viewer_client):
    for bad in ("garbage", "2026-13-40", "06/30/2026", "2026-6-30"):
        res = viewer_client.get(f"/api/dues?as_of={bad}")
        assert res.status_code == 400, (bad, res.status_code)


def test_both_roles_can_read(admin_client, viewer_client):
    assert admin_client.get("/api/dues?as_of=2026-06-30").status_code == 200
    assert viewer_client.get("/api/dues?as_of=2026-06-30").status_code == 200


def test_read_only_writes_nothing(app_env, admin_client):
    """A GET mutates nothing in any table it reads."""
    db = app_env["db_path"]
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=100_000)
    insert_payment(db, unit_number="101", post_date="2025-03-01", amount=50_000)
    before = table_counts(db)
    assert admin_client.get("/api/dues?as_of=2026-06-30").status_code == 200
    assert admin_client.get("/api/dues?as_of=2025-06-30").status_code == 200
    assert table_counts(db) == before


def test_unit_entry_shape(app_env, viewer_client):
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=10_000_000)
    data = get_dues(viewer_client, "2025-06-30")
    assert len(data["units"]) == len(SEEDED_UNITS)
    for u in data["units"]:
        assert set(u.keys()) == UNIT_KEYS
        assert isinstance(u["unit"], str)
        for k in UNIT_KEYS - {"unit"}:
            assert isinstance(u[k], int), (u["unit"], k, u[k])


def test_pre_2025_not_tracked(viewer_client):
    """A pre-2025 as-of date returns 200 with dues not tracked — never an error,
    so the embedded dashboard view degrades gracefully on an early date."""
    data = get_dues(viewer_client, "2024-06-30")
    assert data["dues_tracked"] is False
    assert data["units"] == []
    assert data["operating_budget"] == 0
    assert all(v == 0 for v in data["totals"].values())


def test_2025_is_tracked(viewer_client):
    data = get_dues(viewer_client, "2025-06-30")
    assert data["dues_tracked"] is True
    assert len(data["units"]) == len(SEEDED_UNITS)


def test_totals_identities(app_env, viewer_client):
    """The row identities hold in aggregate (AC6.2)."""
    db = app_env["db_path"]
    clear_budgets(db, 2025)
    insert_budget(db, year=2025, category_name="Insurance Premiums",
                  annual_amount=8_880_000)
    insert_past_due(db, unit_number="101", year=2025, past_due_balance=40_000)
    insert_payment(db, unit_number="202", post_date="2025-05-01", amount=313_000)
    t = get_dues(viewer_client, "2025-06-30")["totals"]
    assert t["expected_total"] == t["carryover"] + t["annual_dues"]
    assert t["outstanding"] == t["expected_total"] - t["paid"]
