# @scaffolding — pins the pure-parser surface (app.ingest) for fast feedback.
# /build may rename the module/functions or reshape ParseResult, logging it in
# build-deviations.md, AS LONG AS the conversion/dedup BEHAVIOR here still holds.
# The durable, @frozen versions of these guarantees are asserted end-to-end
# through the API in test_ingest_upload.py.
"""R2 money, R3 dates, R4 in-file dedup, R7 unknown-account flagging — unit level."""
import pytest

from app import ingest
from conftest import SEEDED_ACCOUNTS, UNKNOWN_ACCT, BANK_HEADER, bank_row, csv_text


# --- R2: exact integer cents ----------------------------------------------

@pytest.mark.parametrize("text, cents", [
    ("371.4", 37140),
    ("625.44", 62544),
    ("3981.85", 398185),
    ("122489.78", 12248978),
    ("$1,234.56", 123456),
    ("  538.07 ", 53807),
    ("-50.00", -5000),
    ("0.00", 0),
])
def test_to_cents_exact(text, cents):
    assert ingest.to_cents(text) == cents


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_to_cents_empty_is_none(empty):
    # An empty Debit/Credit cell is NULL, never 0 (R2).
    assert ingest.to_cents(empty) is None


# --- R3: date normalization, no day-first guessing -------------------------

@pytest.mark.parametrize("raw, iso", [
    ("2/6/2026", "2026-02-06"),
    ("12/31/2025", "2025-12-31"),
    ("1/2/26", "2026-01-02"),
    ("2026-02-06", "2026-02-06"),  # already-ISO passes through
])
def test_normalize_date_ok(raw, iso):
    assert ingest.normalize_date(raw) == iso


@pytest.mark.parametrize("bad", ["", "not-a-date", "25/12/2026", "13/1/2026"])
def test_normalize_date_rejects_unparseable_and_day_first(bad):
    # "25/12/2026" / "13/1/2026" are only valid read day-first; the parser must
    # NOT guess D/M/Y and store a wrong date — it returns None (R3).
    assert ingest.normalize_date(bad) is None


# --- R4: dedup identity is NULL-aware --------------------------------------

def test_dedup_key_null_aware():
    k_null_a = ingest.dedup_key("****9226", "2026-02-06", "Dividend/Interest",
                                None, 2515, 12126832)
    k_null_b = ingest.dedup_key("****9226", "2026-02-06", "Dividend/Interest",
                                None, 2515, 12126832)
    k_zero = ingest.dedup_key("****9226", "2026-02-06", "Dividend/Interest",
                              0, 2515, 12126832)
    assert k_null_a == k_null_b          # two NULL-debit rows share identity
    assert k_null_a != k_zero            # NULL debit is distinct from 0 debit


# --- R1/R7 via the pure parser ---------------------------------------------

def test_missing_columns_detected():
    header = [c for c in BANK_HEADER if c != "Balance"]
    rows = [["****9226", "2/6/2026", "", "x", "1.00", "", "Posted"]]
    result = ingest.parse_csv(csv_text(rows, header=header), SEEDED_ACCOUNTS)
    assert result.errors  # structural error; caller must reject the upload


def test_unknown_account_flagged():
    content = csv_text([
        bank_row(UNKNOWN_ACCT, "2/6/2026", "Mystery", debit="10.00", balance="90.00"),
    ])
    result = ingest.parse_csv(content, SEEDED_ACCOUNTS)
    assert not result.errors
    assert UNKNOWN_ACCT in set(result.unknown_accounts)
    # imported, not dropped — tagged Unknown
    assert any(r.account_name == "Unknown" for r in result.rows)


def test_in_file_duplicate_collapsed():
    row = bank_row("****9226", "1/31/2026", "Dividend/Interest",
                   credit="25.15", balance="121268.32")
    result = ingest.parse_csv(csv_text([row, row]), SEEDED_ACCOUNTS)
    assert not result.errors
    assert result.duplicate_count >= 1
    assert len(result.rows) == 1  # the repeat is not carried as a second row
