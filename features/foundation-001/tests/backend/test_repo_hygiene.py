"""A7 / E5 / BC2 — secrets are not committed; .env.example documents required keys."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
REQUIRED_KEYS = ["ADMIN_PASSWORD_HASH", "BOARD_PASSWORD_HASH", "SESSION_SECRET", "DATABASE_PATH"]


def _find_env_example():
    for candidate in (REPO_ROOT / ".env.example", REPO_ROOT / "backend" / ".env.example"):
        if candidate.exists():
            return candidate
    return None


def test_env_example_lists_required_keys():
    env_example = _find_env_example()
    assert env_example is not None, ".env.example must exist (repo root or backend/)"
    text = env_example.read_text(encoding="utf-8")
    for key in REQUIRED_KEYS:
        assert key in text, f".env.example missing key: {key}"


def test_no_plaintext_secrets_committed():
    env_example = _find_env_example()
    assert env_example is not None
    # .env.example must carry keys with NO values (e.g. "SESSION_SECRET=" empty)
    for line in env_example.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert "=" in line, f"malformed .env.example line: {line!r}"
        _, _, value = line.partition("=")
        assert value.strip() == "", f".env.example must not contain a value: {line!r}"
    # a real .env with secrets must never be committed
    assert not (REPO_ROOT / ".env").exists(), ".env must not be committed"
    assert not (REPO_ROOT / "backend" / ".env").exists(), "backend/.env must not be committed"
