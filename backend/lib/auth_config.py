"""Basic-auth credentials for /api/predict, read from the environment.

Credentials are never baked into the image. docker compose passes ``NGPSUITE_USERNAME`` and
``NGPSUITE_PASSWORD`` (from backend/.env). If they are unset or empty, the placeholders below
are used; they are the same values the web UI uses by default, so a fresh install works
without configuration.

Run ``python -m lib.auth_config`` once before starting the workers to print a notice or a
warning about placeholder credentials. It always exits 0: the service starts either way.
"""
import os
import sys

DEFAULT_USERNAME = "your_username"
DEFAULT_PASSWORD = "your_password"
DEFAULT_BIND = "127.0.0.1"

_LOOPBACK = ("127.0.0.1", "::1", "localhost")


def load_credentials(env=None):
    """Return (username, password); empty or unset values fall back to the placeholders."""
    env = os.environ if env is None else env
    username = env.get("NGPSUITE_USERNAME") or DEFAULT_USERNAME
    password = env.get("NGPSUITE_PASSWORD") or DEFAULT_PASSWORD
    return username, password


def is_default(username, password):
    """True if either value is still a placeholder (the placeholder pair is public knowledge)."""
    return username == DEFAULT_USERNAME or password == DEFAULT_PASSWORD


def is_loopback(bind):
    return (bind or DEFAULT_BIND).strip().lower() in _LOOPBACK


def build_message(env=None):
    """Return the text to print for the current settings, or None when nothing needs saying."""
    env = os.environ if env is None else env
    username, password = load_credentials(env)
    if not is_default(username, password):
        return None

    bind = env.get("NGPSUITE_BIND") or DEFAULT_BIND
    if is_loopback(bind):
        return (
            "NOTICE: default credentials (your_username / your_password) are in use, so "
            "authentication is effectively disabled. This is fine while the service is reachable "
            "only from this machine. To change them, see 'Authentication' in README.md."
        )
    return (
        f"WARNING: default credentials (your_username / your_password) are in use while port 443 "
        f"is published on {bind}. Anyone who can reach this machine on the network can call "
        "/api/predict, and the response contains information derived from GMDB patients. "
        "Set NGPSUITE_USERNAME and NGPSUITE_PASSWORD in backend/.env (and enter the same values "
        "in the web UI Settings), or set NGPSUITE_BIND=127.0.0.1. Do not expose this service to "
        "the internet. See 'Authentication' in README.md."
    )


def main():
    message = build_message()
    if message:
        print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
