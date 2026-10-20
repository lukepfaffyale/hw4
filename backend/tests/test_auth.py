"""Auth security boundary tests. Run from backend/: venv\\Scripts\\python -m pytest -q

Uses a throwaway copy of the course database so the real file is never written by tests.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_REAL_DATA = _HERE.parent.parent / "data"
_TMP = Path(tempfile.mkdtemp(prefix="cc-auth-test-"))
shutil.copy(_REAL_DATA / "campus_customs.db", _TMP / "campus_customs.db")
(_TMP / "products").mkdir()
os.environ["DATA_DIR"] = str(_TMP)
os.environ["SESSION_SECRET"] = "test-secret-not-for-production"
os.environ["HUNT_DATE"] = "2026-10-31"  # every daily friend is out
os.environ.pop("PASSWORD_SCHEME", None)

from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import main  # noqa: E402

SEEDED_EMAIL = "test@campuscustoms.yale.edu"
SEEDED_PASSWORD = "password"
STRONG = "Pumpkin-Lantern-77!"


@pytest.fixture(autouse=True)
def _reset_limits():
    main.auth_ip_limiter.reset()
    main.auth_email_limiter.reset()
    main.hunt_limiter.reset()
    yield


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


# ------------------------------------------------------------------ hashing


def test_hash_is_not_plaintext_and_is_bcrypt_by_default():
    h = auth.hash_password(STRONG)
    assert STRONG not in h
    assert h.startswith("$2b$12$")
    assert auth.verify_password(STRONG, h)
    assert not auth.verify_password(STRONG + "x", h)


def test_two_hashes_of_same_password_differ_because_salt_is_random():
    assert auth.hash_password(STRONG) != auth.hash_password(STRONG)


def test_pbkdf2_scheme_matches_course_format(monkeypatch):
    monkeypatch.setenv("PASSWORD_SCHEME", "pbkdf2")
    h = auth.hash_password(STRONG)
    algo, salt, digest = h.split("$")
    assert algo == "pbkdf2_sha256" and len(salt) == 16 and len(digest) == 64
    assert auth.verify_password(STRONG, h)
    assert not auth.verify_password("wrong-Password-1!", h)


def test_seeded_style_string_verifies_with_salt_as_raw_string():
    # Same construction as the course data pack: salt used as its UTF-8 bytes, 120,000 iterations.
    import hashlib

    salt = "hw4testsalt0001"
    digest = hashlib.pbkdf2_hmac("sha256", b"password", salt.encode(), 120_000).hex()
    stored = f"pbkdf2_sha256${salt}${digest}"
    assert auth.verify_password("password", stored)
    assert not auth.verify_password("Password", stored)


def test_unusable_marker_never_verifies():
    assert not auth.verify_password("!social", auth.UNUSABLE_PASSWORD)
    assert not auth.verify_password("", "$2b$12$whatever")
    assert not auth.verify_password(STRONG, None)
    assert not auth.verify_password(STRONG, "md5$abc$def")


# ------------------------------------------------------------------ policy


@pytest.mark.parametrize(
    "bad",
    [
        "short1!A",  # too short
        "alllowercase123!",  # no uppercase
        "ALLUPPERCASE123!",  # no lowercase
        "NoDigitsHere!!",  # no number
        "NoSymbolsHere123",  # no symbol
        "Has Spaces Here1!",  # spaces
        "Password12345!",  # common base
        "!StartsWithBang1",  # leading !
        "Aaaa1111!!!!bbbb",  # repeated 4x
    ],
)
def test_weak_passwords_are_rejected(bad):
    assert auth.password_issues(bad)


def test_password_cannot_contain_name_or_email():
    assert auth.password_issues("Luke-Rocks-2026!", first_name="Luke")
    assert auth.password_issues("campus-Customs-9!", email="campus@yale.edu")


def test_strong_password_passes():
    assert auth.password_issues(STRONG, email="a@b.edu", first_name="Ada", last_name="Lovelace") == []


# ------------------------------------------------------------------ tokens


def test_session_token_roundtrip_and_tamper():
    token, exp = auth.make_session_token(42)
    assert exp > time.time()
    assert auth.read_session_token(token) == 42
    body, sig = token.rsplit(".", 1)
    assert auth.read_session_token(body + "." + ("0" * len(sig))) is None
    assert auth.read_session_token(token + "x") is None
    assert auth.read_session_token("") is None


def test_expired_token_rejected():
    token, _ = auth.make_session_token(7, ttl=-1)
    assert auth.read_session_token(token) is None


# ------------------------------------------------------------------ API acceptance


def test_seeded_user_logs_in_and_wrong_password_fails(client):
    ok = client.post("/auth/login", json={"email": SEEDED_EMAIL, "password": SEEDED_PASSWORD})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["user"]["email"] == SEEDED_EMAIL
    assert "password" not in body["user"] and "password_hash" not in body["user"]

    bad = client.post("/auth/login", json={"email": SEEDED_EMAIL, "password": "nope-nope-1!"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Email or password is incorrect."


def test_unknown_email_gives_same_message(client):
    r = client.post("/auth/login", json={"email": "nobody@example.edu", "password": "whatever-1!A"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Email or password is incorrect."


def test_signup_then_login_then_delete(client):
    email = f"new-{int(time.time() * 1000)}@example.edu"
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": email.upper(),  # stored lower-cased
        "password": STRONG,
        "confirm_password": STRONG,
    }
    created = client.post("/auth/signup", json=payload)
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    assert created.json()["user"]["email"] == email
    assert created.json()["user"]["auth_provider"] == "password"

    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["first_name"] == "Ada"

    again = client.post("/auth/login", json={"email": email, "password": STRONG})
    assert again.status_code == 200

    wrong = client.post("/auth/login", json={"email": email, "password": STRONG + "x"})
    assert wrong.status_code == 401

    dup = client.post("/auth/signup", json=payload)
    assert dup.status_code == 409

    gone = client.delete("/me", headers={"Authorization": f"Bearer {token}"})
    assert gone.status_code == 200 and gone.json()["ok"] is True
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": STRONG}).status_code == 401


def test_stored_hash_is_not_the_password(client):
    import db

    email = f"hash-{int(time.time() * 1000)}@example.edu"
    r = client.post(
        "/auth/signup",
        json={"first_name": "Grace", "last_name": "Hopper", "email": email, "password": STRONG, "confirm_password": STRONG},
    )
    assert r.status_code == 201
    user = db.get_user_by_email(email)
    assert user is not None
    assert STRONG not in user.password_hash
    assert user.password_hash.startswith("$2b$12$")


def test_validation_error_never_echoes_the_password(client):
    weak = "password12345"
    r = client.post(
        "/auth/signup",
        json={"first_name": "A", "last_name": "B", "email": "weak@example.edu", "password": weak, "confirm_password": weak},
    )
    assert r.status_code == 422
    assert weak not in r.text
    assert "input" not in r.text
    assert any("Password needs" in e["msg"] for e in r.json()["detail"])


def test_mismatched_confirmation_rejected(client):
    r = client.post(
        "/auth/signup",
        json={"first_name": "A", "last_name": "B", "email": "mm@example.edu", "password": STRONG, "confirm_password": STRONG + "!"},
    )
    assert r.status_code == 422
    assert any("do not match" in e["msg"] for e in r.json()["detail"])


def test_unknown_fields_rejected(client):
    r = client.post(
        "/auth/login", json={"email": SEEDED_EMAIL, "password": SEEDED_PASSWORD, "admin": True}
    )
    assert r.status_code == 422


def test_login_rate_limit_per_email(client):
    for _ in range(8):
        client.post("/auth/login", json={"email": "limit@example.edu", "password": "bad-Password-1!"})
    r = client.post("/auth/login", json={"email": "limit@example.edu", "password": "bad-Password-1!"})
    assert r.status_code == 429


def test_me_requires_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_coupon_is_one_per_user_and_deleted_with_account(client):
    """Problem 9 moved the coupon behind the hidden-friends collection: three finds earn it,
    the code never changes, and deleting the account removes it."""
    email = f"egg-{int(time.time() * 1000)}@example.edu"
    r = client.post(
        "/auth/signup",
        json={"first_name": "Mei", "last_name": "Kusakabe", "email": email, "password": STRONG, "confirm_password": STRONG},
    )
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    season = client.get("/hunt").json()["current_season"]
    keys = [f["key"] for f in season["friends"]]

    assert client.get("/me/hunt", headers=h).json()["coupon"] is None
    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[0]}).status_code == 401
    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": "pikachu"}, headers=h).status_code == 404
    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[0], "extra": 1}, headers=h).status_code == 422

    for k in keys[:3]:
        last = client.post("/me/hunt/finds", json={"season": season["key"], "character": k}, headers=h)
        assert last.status_code == 200, last.text
    body = last.json()["coupon"]
    assert body["discount_pct"] == 10 and body["scope"] == "one_item" and body["redeemed_at"] is None
    assert len(body["code"].split("-")[-1]) == 4

    again = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[2]}, headers=h).json()
    assert again["unlocked"] == ["already_found"] and again["coupon"]["code"] == body["code"]  # no second code, ever

    assert client.delete("/me", headers=h).status_code == 200
    import db

    assert db.get_user_by_email(email) is None
    assert client.get("/me/hunt", headers=h).status_code == 401


def test_social_login_unconfigured_returns_503(client, monkeypatch):
    monkeypatch.setattr(main, "SUPABASE_URL", "")
    r = client.post("/auth/social", json={"access_token": "x" * 40})
    assert r.status_code == 503
