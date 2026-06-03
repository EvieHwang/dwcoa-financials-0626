"""E3 / E4 — single-app Fly deploy with a gated post-deploy health check."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_flytoml_declares_volume():
    fly = REPO_ROOT / "fly.toml"
    assert fly.exists(), "fly.toml must exist at repo root"
    text = fly.read_text(encoding="utf-8").lower()
    # a mounted volume for the SQLite database
    assert "mounts" in text or "[[mounts]]" in text, "fly.toml must declare a mounted volume"
    assert "destination" in text or "/data" in text


def _deploy_workflow_text():
    wf_dir = REPO_ROOT / ".github" / "workflows"
    if not wf_dir.exists():
        return None
    for path in wf_dir.glob("*.y*ml"):
        text = path.read_text(encoding="utf-8")
        if "deploy" in text.lower() and ("flyctl" in text.lower() or "fly deploy" in text.lower()):
            return text
    return None


def test_workflow_has_gated_health_check():
    text = _deploy_workflow_text()
    assert text is not None, "a Fly deploy workflow must exist under .github/workflows"
    lowered = text.lower()
    # triggered on push to main
    assert "push" in lowered and "main" in lowered
    # deploys, then checks the live health endpoint
    assert "flyctl deploy" in lowered or "fly deploy" in lowered
    assert "/api/health" in lowered, "workflow must probe the live /api/health endpoint"
