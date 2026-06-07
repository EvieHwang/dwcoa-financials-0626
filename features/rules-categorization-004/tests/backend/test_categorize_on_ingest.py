# @frozen — the categorize-on-ingest contract: an upload categorizes each newly
# inserted row by the active rules (matched -> category + not flagged; unmatched ->
# flagged needs_review), reports categorization counts, never re-categorizes a
# deduped existing row, and applies the seeded transfer rule. Verified through the
# real upload endpoint against a real seeded DB.
"""R2 (categorize on ingest) and R8 (transfer rule on the seeded path)."""
from conftest import (
    bank_row, csv_text, upload, connect, row_by_desc, category_id_by_name,
)


def test_upload_matched_row_categorized(admin_client, app_env):
    # Self-contained: create our own rule (don't depend on seed contents), with a
    # distinctive confidence so we can assert the rule's confidence is persisted.
    cat = category_id_by_name(app_env["db_path"], "Other")
    assert admin_client.post("/api/rules", json={
        "pattern": "KAPPA SERVICE", "category_id": cat, "confidence": 90,
    }).status_code == 201

    content = csv_text([
        bank_row("****9242", "1/15/2026", "KAPPA SERVICE Q1",
                 debit="150.00", balance="500.00"),
    ])
    assert upload(admin_client, content).status_code == 200

    row = row_by_desc(app_env["db_path"], "KAPPA SERVICE Q1")
    assert row["category_id"] == cat
    assert row["needs_review"] == 0
    assert row["confidence"] == 90  # the rule's confidence propagates to the row


def test_upload_unmatched_row_flagged(admin_client, app_env):
    content = csv_text([
        bank_row("****9242", "1/16/2026", "ZZQ UNRECOGNIZED VENDOR PAYMENT",
                 debit="42.00", balance="458.00"),
    ])
    assert upload(admin_client, content).status_code == 200

    row = row_by_desc(app_env["db_path"], "ZZQ UNRECOGNIZED VENDOR PAYMENT")
    assert row["category_id"] is None
    assert row["needs_review"] == 1


def test_transfer_rule_categorizes(admin_client, app_env):
    # R8: transfers are an ordinary high-priority seeded rule -> Transfers category.
    content = csv_text([
        bank_row("****9226", "1/5/2026", "Online Transfer to Checking",
                 debit="500.00", balance="9000.00"),
    ])
    assert upload(admin_client, content).status_code == 200

    row = row_by_desc(app_env["db_path"], "Online Transfer to Checking")
    assert row["category_id"] == category_id_by_name(app_env["db_path"], "Transfers")
    assert row["needs_review"] == 0


def test_upload_summary_categorization_counts(admin_client, app_env):
    content = csv_text([
        bank_row("****9242", "1/15/2026", "Cintas Fire Service Q1",
                 debit="150.00", balance="500.00"),          # matched
        bank_row("****9242", "1/16/2026", "ZZQ UNRECOGNIZED VENDOR",
                 debit="42.00", balance="458.00"),            # unmatched
    ])
    body = upload(admin_client, content).json()
    assert body["added"] == 2
    # New, additive summary fields; existing fields untouched.
    assert body["categorized"] == 1
    assert body["needs_review"] == 1


def test_reupload_does_not_recategorize(admin_client, app_env):
    # Upload an unmatched row, then "fix" it directly (category set, not flagged),
    # then re-upload the same file: the deduped row must be left completely alone.
    content = csv_text([
        bank_row("****9242", "1/16/2026", "ZZQ UNRECOGNIZED VENDOR",
                 debit="42.00", balance="458.00"),
    ])
    upload(admin_client, content)
    fixed_cat = category_id_by_name(app_env["db_path"], "Other")
    con = connect(app_env["db_path"])
    try:
        con.execute(
            "UPDATE transactions SET category_id = ?, needs_review = 0 "
            "WHERE description = ?",
            (fixed_cat, "ZZQ UNRECOGNIZED VENDOR"),
        )
        con.commit()
    finally:
        con.close()
    before = row_by_desc(app_env["db_path"], "ZZQ UNRECOGNIZED VENDOR")

    second = upload(admin_client, content).json()
    assert second["added"] == 0  # deduped

    after = row_by_desc(app_env["db_path"], "ZZQ UNRECOGNIZED VENDOR")
    assert after["id"] == before["id"]
    assert after["category_id"] == fixed_cat
    assert after["needs_review"] == 0
