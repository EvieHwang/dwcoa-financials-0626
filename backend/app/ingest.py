"""Ingestion: the pure, testable bank-CSV parsing logic (no FastAPI imports).

Parses a bank-export CSV, validates the header, maps masked account numbers to
account names, converts money to exact integer cents and dates to ISO, and
collapses in-file duplicates against the canonical dedup identity. The account
map is passed in — this module never touches the database. The router
(`app.routers.transactions`) owns the DB read of existing identities and the
atomic insert.

The two highest-value surfaces here are `to_cents` (exact cents) and the dedup
identity (`dedup_key` / in-file collapse).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass, field
from decimal import InvalidOperation

from .money import dollars_to_cents

# The columns this feature reads. `Check` and `Status` are tolerated-absent
# (treated as empty / "Posted"); everything else is required.
REQUIRED_COLUMNS = (
    "Account Number", "Post Date", "Description", "Debit", "Credit", "Balance",
)

UNKNOWN_ACCOUNT_NAME = "Unknown"


@dataclass
class ParsedRow:
    account_number: str
    account_name: str
    post_date: str
    check_number: str | None
    description: str
    debit: int | None
    credit: int | None
    status: str
    balance: int


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unknown_accounts: list[str] = field(default_factory=list)
    duplicate_count: int = 0


# --- R2: exact integer cents ----------------------------------------------

def to_cents(value: str | None) -> int | None:
    """Parse a dollar string to exact integer cents, or `None` for an empty cell.

    Tolerates `$`, thousands commas, and surrounding whitespace. An empty/`None`
    cell is `None` (a NULL amount), never `0`. A non-empty, unparseable value
    raises `ValueError` so the caller can reject the whole upload (R6).
    """
    if value is None:
        return None
    cleaned = value.strip().replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return dollars_to_cents(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"unparseable amount {value!r}") from exc


# --- R3: date normalization, no day-first guessing -------------------------

def normalize_date(value: str | None) -> str | None:
    """Normalize a US bank date (`M/D/YYYY`, `M/D/YY`) or ISO to `YYYY-MM-DD`.

    Returns `None` (never a guess) for anything unparseable. Day-first formats
    are *not* accepted: a month field over 12 simply fails to parse.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    # Already-ISO passes through (idempotent re-ingest of a normalized value).
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


# --- R4: canonical dedup identity ------------------------------------------

def dedup_key(account_number, post_date, description, debit, credit, balance):
    """The canonical, NULL-aware row identity used for in-file and against-store
    dedup. `None` (an empty debit/credit) stays `None` in the tuple, so a
    NULL amount matches only another NULL — never `0`.
    """
    return (account_number, post_date, description, debit, credit, balance)


# --- R1/R2/R3/R4/R7: parse the whole file ----------------------------------

def parse_csv(content: str, account_map: dict[str, str]) -> ParseResult:
    """Parse and validate a bank-export CSV against `account_map`.

    Returns parsed (in-file-deduped) rows plus structured outcomes: `errors`
    (structural + row-level — non-empty means the caller must reject the whole
    upload), `unknown_accounts` (distinct masked numbers seen unmapped, in order),
    and the in-file `duplicate_count`. Pure: no DB access.
    """
    result = ParseResult()

    reader = csv.reader(io.StringIO(content))
    try:
        raw_header = next(reader)
    except StopIteration:
        result.errors.append("The file is empty or not a valid CSV with a header.")
        return result

    header = [h.strip() for h in raw_header]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        result.errors.append(
            "Missing required column(s): " + ", ".join(missing)
        )
        return result

    index = {name: i for i, name in enumerate(header)}

    def cell(record: list[str], name: str) -> str:
        if name not in index:
            return ""
        i = index[name]
        return record[i] if i < len(record) else ""

    seen: set = set()
    for lineno, record in enumerate(reader, start=2):
        if not record or all(c.strip() == "" for c in record):
            continue  # skip wholly-blank lines

        account_number = cell(record, "Account Number").strip()
        description = cell(record, "Description")

        post_raw = cell(record, "Post Date")
        post_date = normalize_date(post_raw)
        if post_date is None:
            result.errors.append(f"Row {lineno}: unparseable date {post_raw!r}")
            continue

        try:
            debit = to_cents(cell(record, "Debit"))
            credit = to_cents(cell(record, "Credit"))
            balance = to_cents(cell(record, "Balance"))
        except ValueError as exc:
            result.errors.append(f"Row {lineno}: {exc}")
            continue
        if balance is None:
            result.errors.append(f"Row {lineno}: Balance is required and was empty.")
            continue

        mapped = account_map.get(account_number)
        if mapped is None:
            account_name = UNKNOWN_ACCOUNT_NAME
            if account_number not in result.unknown_accounts:
                result.unknown_accounts.append(account_number)
        else:
            account_name = mapped

        check_number = cell(record, "Check").strip() or None
        status = cell(record, "Status").strip() or "Posted"

        key = dedup_key(account_number, post_date, description, debit, credit, balance)
        if key in seen:
            result.duplicate_count += 1
            continue
        seen.add(key)

        result.rows.append(
            ParsedRow(
                account_number=account_number,
                account_name=account_name,
                post_date=post_date,
                check_number=check_number,
                description=description,
                debit=debit,
                credit=credit,
                status=status,
                balance=balance,
            )
        )

    return result
