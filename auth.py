"""
Lightweight authentication for CodeMentor AI.

This is intentionally dependency-free (only the Python standard library) so
it runs anywhere main.py already runs -- no new pip installs needed before
your deadline.

Honest security notes (worth putting in your README):
- Passwords are never stored in plain text. We hash them with
  PBKDF2-HMAC-SHA256 + a random salt per user (100,000 iterations). This is
  a real, recognized hashing approach -- not just sha256(password).
- "Sessions" are signed tokens (HMAC-SHA256 over "email:expiry"), not a full
  JWT library, and they expire after 7 days. Good enough for a hackathon
  demo. A production version would add token revocation, refresh tokens,
  and HTTPS-only cookies.
- Users are stored in a local users.json file, not a real database. Fine
  for a demo; a production version would use Postgres/SQLite.
"""

import json
import os
import hmac
import hashlib
import secrets
import time

_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(_DIR, "users.json")

# Set AUTH_SECRET_KEY in your .env for real use. Falls back to a dev key so
# things still work locally if you forget -- just don't ship that fallback.
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-only-change-me")
TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # sessions last 7 days


def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100_000
    ).hex()


def create_account(email: str, password: str, name: str) -> None:
    """Raises ValueError with a user-facing message if signup is invalid."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    users = _load_users()
    if email in users:
        raise ValueError("An account with this email already exists.")

    salt = secrets.token_hex(16)
    users[email] = {
        "name": name.strip() or email.split("@")[0],
        "salt": salt,
        "password_hash": _hash_password(password, salt),
    }
    _save_users(users)


def verify_login(email: str, password: str):
    """Returns the user record on success, or None on bad credentials."""
    email = email.strip().lower()
    user = _load_users().get(email)
    if not user:
        return None
    if _hash_password(password, user["salt"]) != user["password_hash"]:
        return None
    return user


def get_user_name(email: str) -> str:
    user = _load_users().get(email.strip().lower())
    return user["name"] if user else email.split("@")[0]


def make_token(email: str) -> str:
    """Builds a signed, expiring session token. No database lookup needed
    to verify it later -- the signature proves it's legit."""
    email = email.strip().lower()
    expiry = str(int(time.time()) + TOKEN_TTL_SECONDS)
    payload = f"{email}:{expiry}"
    signature = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}:{signature}".encode().hex()


def verify_token(token: str):
    """Returns the email the token belongs to, or None if it's missing,
    tampered with, or expired."""
    try:
        raw = bytes.fromhex(token).decode()
        email, expiry, signature = raw.rsplit(":", 2)
        expected = hmac.new(
            SECRET_KEY.encode(), f"{email}:{expiry}".encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None  # signature doesn't match -- token was tampered with
        if int(expiry) < int(time.time()):
            return None  # session expired
        return email
    except Exception:
        return None