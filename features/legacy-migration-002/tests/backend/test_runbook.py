"""R11 — the operator runbook exists and covers the local-only cutover steps."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNBOOK = REPO_ROOT / "backend" / "docs" / "legacy-import.md"


def test_runbook_documents_cutover():
    assert RUNBOOK.exists(), f"missing runbook at {RUNBOOK}"
    text = RUNBOOK.read_text()
    assert len(text) > 400, "runbook is too thin to be a real procedure"
    lower = text.lower()
    # 1) S3 pull of the legacy DB
    assert "s3://dwcoa-data-070840362692/dwcoa.db" in text
    # 2) running the importer
    assert "app.legacy_import" in text
    # 3) landing the file on the Fly volume
    assert "fly ssh sftp" in lower
    # 4) post-cutover verification
    assert "verif" in lower
