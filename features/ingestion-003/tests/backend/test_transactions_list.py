# @frozen — the public list contract: GET /api/transactions, its filters,
# pagination, ordering, response shape, and auth. The frontend consumes this.
"""R9 (list/filter/paginate), R10 (auth on read)."""
from conftest import insert_txn, connect


def _seed_rows(db_path):
    # Spread across years and accounts; ids ascending in insertion order.
    insert_txn(db_path, account_number="****9242", account_name="Checking",
               post_date="2024-06-01", description="2024 Checking", debit=1000, balance=5000)
    insert_txn(db_path, account_number="****9226", account_name="Reserve Fund",
               post_date="2025-03-15", description="2025 Reserve", credit=2000, balance=7000)
    insert_txn(db_path, account_number="****9242", account_name="Checking",
               post_date="2025-09-20", description="2025 Checking", debit=300, balance=6700)
    insert_txn(db_path, account_number="****9226", account_name="Reserve Fund",
               post_date="2026-01-05", description="2026 Reserve", credit=500, balance=7200)


def test_list_orders_and_fields(admin_client, app_env):
    _seed_rows(app_env["db_path"])
    body = admin_client.get("/api/transactions").json()
    txns = body["transactions"]
    assert body["total"] == 4
    # newest first by post_date
    assert [t["post_date"] for t in txns] == [
        "2026-01-05", "2025-09-20", "2025-03-15", "2024-06-01",
    ]
    # fields the UI needs are present; amounts are integer cents; category null
    top = txns[0]
    for key in ("account_name", "account_number", "post_date", "description",
                "debit", "credit", "balance", "status", "category"):
        assert key in top
    assert top["credit"] == 500
    assert top["category"] is None  # uncategorized until slice 4


def test_pagination_and_total(admin_client, app_env):
    _seed_rows(app_env["db_path"])
    body = admin_client.get("/api/transactions?limit=2&offset=0").json()
    assert len(body["transactions"]) == 2
    assert body["total"] == 4           # total reflects all matching rows, not the page
    page2 = admin_client.get("/api/transactions?limit=2&offset=2").json()
    assert len(page2["transactions"]) == 2
    # the two pages are disjoint
    ids = {t["id"] for t in body["transactions"]} | {t["id"] for t in page2["transactions"]}
    assert len(ids) == 4


def test_limit_is_bounded(admin_client, app_env):
    _seed_rows(app_env["db_path"])
    body = admin_client.get("/api/transactions?limit=1000000").json()
    # an over-large page size is clamped to a bounded maximum (no unbounded page)
    assert body["limit"] <= 1000
    assert len(body["transactions"]) <= body["limit"]


def test_filters_year_account(admin_client, app_env):
    _seed_rows(app_env["db_path"])
    y2025 = admin_client.get("/api/transactions?year=2025").json()
    assert y2025["total"] == 2
    assert all(t["post_date"].startswith("2025") for t in y2025["transactions"])

    checking = admin_client.get("/api/transactions?account=Checking").json()
    assert checking["total"] == 2
    assert all(t["account_name"] == "Checking" for t in checking["transactions"])

    both = admin_client.get("/api/transactions?year=2025&account=Checking").json()
    assert both["total"] == 1
    assert both["transactions"][0]["description"] == "2025 Checking"


def test_includes_all_types(admin_client, app_env):
    # A Transfer/Internal-typed transaction is NOT excluded from this raw list
    # (transfers-excluded reporting is slice 6, not here).
    db_path = app_env["db_path"]
    con = connect(db_path)
    try:
        transfer_cat = con.execute(
            "SELECT id FROM categories WHERE type='Transfer' LIMIT 1"
        ).fetchone()[0]
    finally:
        con.close()
    insert_txn(db_path, account_number="****7145", account_name="Savings",
               post_date="2026-02-01", description="Internal Transfer",
               debit=10000, balance=0, category_id=transfer_cat)
    body = admin_client.get("/api/transactions").json()
    assert any(t["description"] == "Internal Transfer" for t in body["transactions"])


def test_viewer_can_list(viewer_client, app_env):
    _seed_rows(app_env["db_path"])
    r = viewer_client.get("/api/transactions")
    assert r.status_code == 200
    assert r.json()["total"] == 4


def test_list_requires_auth(client):
    # Anonymous (no session) cannot read the list.
    assert client.get("/api/transactions").status_code == 401
