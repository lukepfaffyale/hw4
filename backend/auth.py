"""Passwords, password policy and session tokens. One security boundary, tested in tests/test_auth.py.

Stored password formats in `users.password_hash`:

- Seeded accounts (course data pack): ``pbkdf2_sha256$<salt>$<hexdigest>``. PBKDF2-HMAC-SHA256,
  120,000 iterations, the salt used as its UTF-8 string bytes (not hex-decoded), digest as hex.
  Verified exactly that way. The salt is read from the stored value; never regenerated at login.
- New accounts (default): bcrypt, cost 12. bcrypt generates a unique random salt per password and
  stores it inside the hash (``$2b$12$...``). This is the class rule. Set ``PASSWORD_SCHEME=pbkdf2``
  to write new accounts in the course format instead; login verifies both formats regardless.
- Social accounts: the unusable marker ``!social``. No typed password can ever verify against it.

The plaintext password is never stored, logged, or returned. Comparison is constant-time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import warnings

import bcrypt

PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120_000
BCRYPT_ROUNDS = 12
UNUSABLE_PASSWORD = "!social"
BCRYPT_MAX_BYTES = 72

# A real bcrypt hash of a random string, used so a login for an unknown email takes as long as a
# login for a known one (no user-enumeration by timing).
_DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(24), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("ascii")


# ------------------------------------------------------------------ hashing


def password_scheme() -> str:
    return (os.environ.get("PASSWORD_SCHEME") or "bcrypt").strip().lower()


def _pbkdf2_hex(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    """Hash a new password. Never returns or logs the plaintext."""
    if password.startswith("!"):
        # "!..." is reserved for unusable markers; the policy already forbids leading "!".
        raise ValueError("invalid password")
    if password_scheme() == "pbkdf2":
        salt = secrets.token_hex(8)  # 16 hex chars, same shape as the seeded rows
        return f"{PBKDF2_PREFIX}${salt}${_pbkdf2_hex(password, salt)}"
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check of a typed password against a stored hash of either format."""
    if not password or not stored or stored.startswith("!"):
        return False
    if stored.startswith(PBKDF2_PREFIX + "$"):
        parts = stored.split("$")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            return False
        _, salt, digest = parts
        return hmac.compare_digest(_pbkdf2_hex(password, salt), digest)
    if stored.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("ascii"))
        except ValueError:
            return False
    return False


def burn_time_like_a_real_check(password: str) -> None:
    """Called when the email is unknown so the response time matches a real verification."""
    verify_password(password, _DUMMY_HASH)


# ------------------------------------------------------------------ password policy

PASSWORD_MIN = 12
PASSWORD_MAX = 64
_COMMON = {
    "password", "password1", "password123", "passw0rd", "qwerty", "letmein", "welcome",
    "iloveyou", "admin", "123456", "12345678", "123456789", "1234567890", "abc123", "monkey",
    "dragon", "football", "baseball", "sunshine", "princess", "trustno1", "yale", "bulldogs",
    "campuscustoms", "changeme", "secret123", "letmein1",
}


def password_issues(
    password: str, *, email: str = "", first_name: str = "", last_name: str = ""
) -> list[str]:
    """Return every rule the password breaks (empty list means it passes)."""
    issues: list[str] = []
    if len(password) < PASSWORD_MIN:
        issues.append(f"at least {PASSWORD_MIN} characters")
    if len(password) > PASSWORD_MAX:
        issues.append(f"at most {PASSWORD_MAX} characters")
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        issues.append(f"at most {BCRYPT_MAX_BYTES} bytes")
    if not re.search(r"[a-z]", password):
        issues.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        issues.append("an uppercase letter")
    if not re.search(r"[0-9]", password):
        issues.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        issues.append("a symbol")
    if re.search(r"\s", password):
        issues.append("no spaces")
    if password.startswith("!"):
        issues.append("must not start with !")
    lowered = password.lower()
    squashed = re.sub(r"[^a-z0-9]", "", lowered)
    if (
        lowered in _COMMON
        or squashed in _COMMON
        or any(len(w) >= 6 and w in squashed for w in _COMMON)
    ):
        issues.append("not based on a common password")
    for label, value in (("your email", email.split("@")[0]), ("your first name", first_name), ("your last name", last_name)):
        v = value.strip().lower()
        if len(v) >= 3 and v in lowered:
            issues.append(f"must not contain {label}")
    if re.search(r"(.)\1\1\1", password):
        issues.append("no character repeated 4 times in a row")
    return issues


# ------------------------------------------------------------------ session tokens

SESSION_TTL_SECONDS = 7 * 24 * 3600
_generated_secret: bytes | None = None


def _secret() -> bytes:
    global _generated_secret
    value = (os.environ.get("SESSION_SECRET") or "").strip()
    if value:
        return value.encode("utf-8")
    if _generated_secret is None:
        _generated_secret = secrets.token_bytes(32)
        warnings.warn(
            "SESSION_SECRET is not set; using a random secret for this process. "
            "Sessions will not survive a restart. Set SESSION_SECRET in backend/.env.",
            stacklevel=2,
        )
    return _generated_secret


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_session_token(user_id: int, ttl: int = SESSION_TTL_SECONDS) -> tuple[str, int]:
    """Return (token, expires_at_epoch). The token carries only the user id and expiry."""
    exp = int(time.time()) + ttl
    payload = {"uid": int(user_id), "exp": exp, "n": secrets.token_hex(4)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}", exp


def read_session_token(token: str | None) -> int | None:
    """Return the user id if the token is well-formed, signed by us, and not expired."""
    if not token or "." not in token or len(token) > 512:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(_unb64(body))
        uid = int(payload["uid"])
        exp = int(payload["exp"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if exp < time.time():
        return None
    return uid
