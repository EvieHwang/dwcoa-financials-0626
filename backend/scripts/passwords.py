"""Generate and verify the bcrypt password hashes the app expects.

Why this exists: `ADMIN_PASSWORD_HASH` / `BOARD_PASSWORD_HASH` are bcrypt hashes
that always contain `$` characters (`$2b$12$...`). If they are set through a
shell *without single quotes* — `export ADMIN_PASSWORD_HASH=$2b$12$...` or
`fly secrets set ADMIN_PASSWORD_HASH=$2b$12$...` — the shell expands `$2b`,
`$12`, ... as (empty) variables and the stored value is silently corrupted.
The app then rejects the *correct* password with "Incorrect password."

Usage
-----
Generate a hash (the password is read from a prompt, never the shell history):

    python -m scripts.passwords hash

Verify a password against a stored/candidate hash (use this to confirm what is
actually deployed matches the intended password):

    python -m scripts.passwords verify '<bcrypt-hash>'

Always wrap the resulting hash in SINGLE quotes when you set it:

    export ADMIN_PASSWORD_HASH='$2b$12$....'
    fly secrets set ADMIN_PASSWORD_HASH='$2b$12$....'
"""
from __future__ import annotations

import getpass
import sys

import bcrypt

# Reuse the exact verification the app uses, so "verify" mirrors production.
sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from app.auth import verify_password  # noqa: E402


def _read_password(prompt: str) -> str:
    pw = getpass.getpass(prompt)
    if not pw:
        sys.exit("Empty password; aborting.")
    return pw


def cmd_hash() -> None:
    pw = _read_password("Password to hash: ")
    if _read_password("Confirm password: ") != pw:
        sys.exit("Passwords did not match; aborting.")
    digest = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    print(digest)
    print(
        "\nSet it with SINGLE quotes so the shell does not eat the '$' segments:\n"
        f"  export ADMIN_PASSWORD_HASH='{digest}'\n"
        f"  fly secrets set ADMIN_PASSWORD_HASH='{digest}'",
        file=sys.stderr,
    )


def cmd_verify(password_hash: str) -> None:
    pw = _read_password("Password to check: ")
    if verify_password(pw, password_hash):
        print("MATCH: this password verifies against the given hash.")
    else:
        print("NO MATCH: the password does not verify against the given hash.")
        if not password_hash.startswith(("$2a$", "$2b$", "$2y$")):
            print(
                "  ^ the hash doesn't start with a bcrypt prefix ($2b$...). It was "
                "probably corrupted by unquoted shell expansion when it was set.",
                file=sys.stderr,
            )
        sys.exit(1)


def main(argv: list[str]) -> None:
    if len(argv) >= 1 and argv[0] == "hash":
        cmd_hash()
    elif len(argv) == 2 and argv[0] == "verify":
        cmd_verify(argv[1])
    else:
        sys.exit(
            "usage:\n"
            "  python -m scripts.passwords hash\n"
            "  python -m scripts.passwords verify '<bcrypt-hash>'"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
