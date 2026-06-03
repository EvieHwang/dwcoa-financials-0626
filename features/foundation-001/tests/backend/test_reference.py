"""Story C (API side) — the reference endpoint returns seeded data."""


def test_reference_requires_auth(client):
    assert client.get("/api/reference").status_code == 401


def test_reference_returns_seeded_data(viewer_client):
    r = viewer_client.get("/api/reference")
    assert r.status_code == 200
    data = r.json()
    # 9 units present with ownership
    units = {u["number"]: u for u in data["units"]}
    assert set(units) == {"101", "102", "103", "201", "202", "203", "301", "302", "303"}
    assert abs(float(units["101"]["ownership_pct"]) - 0.117) < 1e-9
    assert abs(float(units["202"]["ownership_pct"]) - 0.104) < 1e-9
    # 3 accounts mapped
    accounts = {a["name"] for a in data["accounts"]}
    assert accounts == {"Savings", "Checking", "Reserve Fund"}
    # categories include known income + expense names
    cat_names = {c["name"] for c in data["categories"]}
    assert {"Dues 101", "Grounds/Landscaping", "Transfers"} <= cat_names
