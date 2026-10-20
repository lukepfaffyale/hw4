"""The only module that touches `data/campus_customs.db`.

Rules: parameterised queries only, rows mapped to typed objects before they leave this file,
no client-supplied strings ever reach a file path, every user-scoped query takes the user id
from the verified session, never from the client.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from models import (
    SIZE_ORDER,
    Category,
    Coupon,
    ProductDetail,
    ProductQuery,
    ProductSummary,
    Reward,
    Size,
    StockLevel,
    UserPublic,
)

HERE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR") or (HERE.parent / "data")).resolve()
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCTS_DIR = DATA_DIR / "products"

LOW_STOCK_AT = 5
SHORT_DESCRIPTION_CHARS = 110


class EmailTaken(Exception):
    """Raised when a signup email already exists."""


@contextmanager
def connect(*, write: bool = False) -> Iterator[sqlite3.Connection]:
    """One connection per request. Read-only unless `write=True`. Foreign keys on, rows by name."""
    if not DB_PATH.is_file():
        raise RuntimeError(f"Database not found at {DB_PATH}. Unzip the data pack into data/.")
    mode = "rw" if write else "ro"
    con = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        if write:
            con.commit()
    except Exception:
        if write:
            con.rollback()
        raise
    finally:
        con.close()


def ensure_schema() -> None:
    """Idempotent additions on top of the shipped schema. Logged in docs/data/CHANGELOG.md."""
    with connect(write=True) as con:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(users)")}
        if "auth_provider" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'password'")
        if "provider_user_id" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN provider_user_id TEXT")
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, created_at)"
        )
        # Easter-egg coupons: one per shopper (UNIQUE user_id), good for one item, once.
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS coupons (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL UNIQUE,
                code            TEXT NOT NULL UNIQUE,
                discount_pct    INTEGER NOT NULL DEFAULT 10,
                scope           TEXT NOT NULL DEFAULT 'one_item',
                found_character TEXT NOT NULL,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                redeemed_at     TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        # Problem 9: hidden-friends collection, referrals, bigger rewards, restock requests.
        if "referral_code" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
        if "referred_by" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER REFERENCES users(id) ON DELETE SET NULL")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
        for row in con.execute("SELECT id FROM users WHERE referral_code IS NULL").fetchall():
            con.execute("UPDATE users SET referral_code = ? WHERE id = ?", (_new_referral_code(), int(row["id"])))
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS egg_finds (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL REFERENCES users(id),
                season           TEXT NOT NULL,
                character        TEXT NOT NULL,
                source           TEXT NOT NULL DEFAULT 'found',
                referred_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at       TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_egg_finds_found ON egg_finds(user_id, season, character) WHERE source = 'found'"
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_egg_finds_referred ON egg_finds(referred_user_id) WHERE referred_user_id IS NOT NULL"
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS rewards (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id),
                kind          TEXT NOT NULL,
                code          TEXT NOT NULL UNIQUE,
                max_value_usd INTEGER NOT NULL DEFAULT 100,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                redeemed_at   TEXT,
                UNIQUE (user_id, kind)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS restock_requests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                product_id TEXT NOT NULL REFERENCES catalogue(product_id),
                size       TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_restock_open ON restock_requests(user_id, product_id, size) WHERE status = 'open'"
        )


_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _new_referral_code() -> str:
    return "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(8))


# ------------------------------------------------------------------ mapping helpers


def normalise_category(garment_type: str) -> Category:
    """Collapse the 22 free-text garment types into the categories the shop filters on."""
    g = garment_type.lower()
    if "hood" in g:
        return "hoodie"
    if "quarter" in g or "1/4" in g:
        return "quarter-zip"
    if "jacket" in g or "bomber" in g or "full-zip" in g:
        return "jacket"
    if "performance" in g:
        return "performance"
    if "t-shirt" in g or "tee" in g:
        return "t-shirt"
    if "crew" in g or "mockneck" in g or "sweatshirt" in g:
        return "crewneck"
    return "other"


def _json_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def _short(text: str, limit: int = SHORT_DESCRIPTION_CHARS) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def _status(quantity: int) -> str:
    if quantity <= 0:
        return "sold_out"
    if quantity <= LOW_STOCK_AT:
        return "low"
    return "in_stock"


def image_url_for(product_id: str) -> str:
    return f"/media/products/{product_id}"


def _summary(row: sqlite3.Row, total_stock: int, sizes_in_stock: list[Size]) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=normalise_category(row["garment_type"]),
        short_description=_short(row["description"]),
        colors=_json_list(row["colors"]),
        price=float(row["price"]),
        image_url=image_url_for(row["product_id"]),
        total_stock=total_stock,
        sizes_in_stock=sizes_in_stock,
    )


def _iso_utc(sqlite_ts: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' (SQLite datetime('now'), UTC) -> ISO 8601 with Z."""
    return sqlite_ts.replace(" ", "T") + "Z" if sqlite_ts and "T" not in sqlite_ts else sqlite_ts


# ------------------------------------------------------------------ products


def list_products(query: ProductQuery) -> tuple[list[ProductSummary], list[Category]]:
    """All products matching the query, plus the categories present in the catalogue."""
    with connect() as con:
        rows = con.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
        # Sizes in stock per product, one query for the whole grid (Problem 9: size chips on cards).
        in_stock: dict[str, list[Size]] = {}
        for r in con.execute("SELECT product_id, size FROM inventory WHERE quantity > 0").fetchall():
            if r["size"] in SIZE_ORDER:
                in_stock.setdefault(r["product_id"], []).append(r["size"])

    items = [
        _summary(r, int(r["total_stock"]), sorted(in_stock.get(r["product_id"], []), key=SIZE_ORDER.index))
        for r in rows
    ]
    categories = sorted({p.category for p in items})

    if query.sort == "price_asc":
        items.sort(key=lambda p: (p.price, p.name))
    elif query.sort == "price_desc":
        items.sort(key=lambda p: (-p.price, p.name))
    elif query.sort == "name":
        items.sort(key=lambda p: p.name)

    if query.category:
        items = [p for p in items if p.category == query.category]
    if query.max_price is not None:
        items = [p for p in items if p.price <= query.max_price]
    if query.in_stock:
        items = [p for p in items if p.total_stock > 0]
    if query.q:
        needle = query.q.lower().strip()
        if needle:
            # Search name, type, description, colours and tags. Tags are data, not instructions.
            with connect() as con:
                hits = {
                    r["product_id"]
                    for r in con.execute(
                        """
                        SELECT product_id FROM catalogue
                        WHERE lower(name) LIKE :n OR lower(garment_type) LIKE :n
                           OR lower(description) LIKE :n OR lower(colors) LIKE :n
                           OR lower(search_tags) LIKE :n
                        """,
                        {"n": f"%{needle}%"},
                    )
                }
            items = [p for p in items if p.product_id in hits]

    return items, categories


def get_product(product_id: str) -> ProductDetail | None:
    with connect() as con:
        row = con.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        inv = con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    by_size: dict[str, int] = {r["size"]: int(r["quantity"]) for r in inv}
    stock: list[StockLevel] = []
    for size in SIZE_ORDER:
        if size in by_size:
            q = by_size[size]
            stock.append(StockLevel(size=size, quantity=q, status=_status(q)))  # type: ignore[arg-type]
    total = sum(s.quantity for s in stock)
    sizes_in: list[Size] = [s.size for s in stock if s.quantity > 0]

    base = _summary(row, total, sizes_in)
    return ProductDetail(
        **base.model_dump(),
        description=row["description"],
        search_tags=_json_list(row["search_tags"]),
        stock=stock,
    )


def image_path_for(product_id: str) -> Path | None:
    """Resolve a product's image from the catalogue row, never from the request string.

    Returns None when the product does not exist or the stored path escapes `data/products/`.
    """
    with connect() as con:
        row = con.execute(
            "SELECT image_file_path FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
    if row is None:
        return None
    candidate = (DATA_DIR / row["image_file_path"]).resolve()
    try:
        candidate.relative_to(PRODUCTS_DIR)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


# ------------------------------------------------------------------ users


@dataclass(frozen=True)
class UserRecord:
    """A `users` row for back-end use only. Carries the hash; never serialised to a client."""

    id: int
    first_name: str
    last_name: str
    email: str
    password_hash: str
    auth_provider: str
    provider_user_id: str | None
    created_at: str
    referral_code: str | None = None
    referred_by: int | None = None

    def public(self, *, is_admin: bool = False) -> UserPublic:
        return UserPublic(
            id=self.id,
            first_name=self.first_name,
            last_name=self.last_name,
            email=self.email,
            auth_provider=self.auth_provider,  # type: ignore[arg-type]
            created_at=_iso_utc(self.created_at),
            is_admin=is_admin,
        )


def _user(row: sqlite3.Row | None) -> UserRecord | None:
    if row is None:
        return None
    keys = row.keys()
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    last = row["last_name"] or " ".join((row["name"] or "").split(" ")[1:])
    return UserRecord(
        id=int(row["id"]),
        first_name=first,
        last_name=last,
        email=row["email"],
        password_hash=row["password_hash"],
        auth_provider=row["auth_provider"] or "password",
        provider_user_id=row["provider_user_id"],
        created_at=row["created_at"],
        referral_code=row["referral_code"] if "referral_code" in keys else None,
        referred_by=int(row["referred_by"]) if "referred_by" in keys and row["referred_by"] is not None else None,
    )


def get_user_by_email(email: str) -> UserRecord | None:
    with connect() as con:
        return _user(con.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone())


def get_user_by_id(user_id: int) -> UserRecord | None:
    with connect() as con:
        return _user(con.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone())


def get_user_by_provider(provider: str, provider_user_id: str) -> UserRecord | None:
    with connect() as con:
        return _user(
            con.execute(
                "SELECT * FROM users WHERE auth_provider = ? AND provider_user_id = ?",
                (provider, provider_user_id),
            ).fetchone()
        )


def create_user(
    *,
    first_name: str,
    last_name: str,
    email: str,
    password_hash: str,
    auth_provider: str = "password",
    provider_user_id: str | None = None,
    referred_by: int | None = None,
) -> UserRecord:
    """Insert a user. `password_hash` is already hashed (or the unusable marker). Raises EmailTaken."""
    email = email.lower()
    try:
        with connect(write=True) as con:
            cur = con.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name, auth_provider, provider_user_id,
                                   referral_code, referred_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{first_name} {last_name}".strip(),
                    email,
                    password_hash,
                    first_name,
                    last_name,
                    auth_provider,
                    provider_user_id,
                    _new_referral_code(),
                    referred_by,
                ),
            )
            new_id = int(cur.lastrowid or 0)
    except sqlite3.IntegrityError as exc:
        if "users.email" not in str(exc) and "referral_code" in str(exc):
            # A referral code collision (1 in 10^12): try once more.
            return create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=password_hash,
                auth_provider=auth_provider,
                provider_user_id=provider_user_id,
                referred_by=referred_by,
            )
        raise EmailTaken(email) from exc
    created = get_user_by_id(new_id)
    assert created is not None
    return created


def get_user_by_referral_code(code: str) -> UserRecord | None:
    with connect() as con:
        return _user(con.execute("SELECT * FROM users WHERE referral_code = ?", (code.upper(),)).fetchone())


def link_social(user_id: int, provider: str, provider_user_id: str) -> None:
    with connect(write=True) as con:
        con.execute(
            "UPDATE users SET auth_provider = ?, provider_user_id = ? WHERE id = ?",
            (provider, provider_user_id, int(user_id)),
        )


def delete_user(user_id: int) -> int:
    """Delete the user's chat history, finds, coupon, rewards, restock requests and account.
    Returns the number of chat rows removed. A referral credit someone else earned from this
    account is kept but unlinked (no PII remains in it)."""
    uid = int(user_id)
    with connect(write=True) as con:
        cur = con.execute("DELETE FROM chat_messages WHERE user_id = ?", (uid,))
        removed = cur.rowcount if cur.rowcount is not None else 0
        con.execute("DELETE FROM coupons WHERE user_id = ?", (uid,))
        con.execute("DELETE FROM egg_finds WHERE user_id = ?", (uid,))
        con.execute("UPDATE egg_finds SET referred_user_id = NULL WHERE referred_user_id = ?", (uid,))
        con.execute("DELETE FROM rewards WHERE user_id = ?", (uid,))
        con.execute("DELETE FROM restock_requests WHERE user_id = ?", (uid,))
        con.execute("UPDATE users SET referred_by = NULL WHERE referred_by = ?", (uid,))
        con.execute("DELETE FROM users WHERE id = ?", (uid,))
    return max(removed, 0)


# ------------------------------------------------------------------ chat history


@dataclass(frozen=True)
class ChatRow:
    id: int
    role: str
    content: str
    products_json: str | None
    created_at: str


def list_chat_messages(user_id: int, limit: int = 40) -> list[ChatRow]:
    """The shopper's own turns, oldest first, capped to the most recent `limit`."""
    with connect() as con:
        rows = con.execute(
            """
            SELECT id, role, content, products_json, created_at FROM chat_messages
            WHERE user_id = ? ORDER BY id DESC LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
    return [
        ChatRow(int(r["id"]), r["role"], r["content"], r["products_json"], _iso_utc(r["created_at"]))
        for r in reversed(rows)
    ]


def add_chat_message(user_id: int, role: str, content: str, products_json: str | None) -> int:
    with connect(write=True) as con:
        cur = con.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (int(user_id), role, content, products_json),
        )
        return int(cur.lastrowid or 0)


def delete_chat_messages(user_id: int) -> int:
    with connect(write=True) as con:
        cur = con.execute("DELETE FROM chat_messages WHERE user_id = ?", (int(user_id),))
        return max(cur.rowcount or 0, 0)


# ------------------------------------------------------------------ coupons


def _coupon(row: sqlite3.Row | None, *, already_claimed: bool) -> Coupon | None:
    if row is None:
        return None
    return Coupon(
        code=row["code"],
        discount_pct=int(row["discount_pct"]),
        scope=row["scope"],
        found_character=row["found_character"],
        created_at=_iso_utc(row["created_at"]),
        redeemed_at=_iso_utc(row["redeemed_at"]) if row["redeemed_at"] else None,
        already_claimed=already_claimed,
    )


def get_coupon(user_id: int) -> Coupon | None:
    with connect() as con:
        row = con.execute("SELECT * FROM coupons WHERE user_id = ?", (int(user_id),)).fetchone()
    return _coupon(row, already_claimed=True)


def claim_coupon(user_id: int, character: str, make_code: Callable[[], str]) -> Coupon:
    """Give the shopper their single coupon. A second claim returns the existing one unchanged."""
    existing = get_coupon(user_id)
    if existing is not None:
        return existing
    for _ in range(5):
        code = make_code()
        try:
            with connect(write=True) as con:
                con.execute(
                    "INSERT INTO coupons (user_id, code, found_character) VALUES (?, ?, ?)",
                    (int(user_id), code, character),
                )
            break
        except sqlite3.IntegrityError:
            # Either the code collided (retry) or the user already has one (return it below).
            if get_coupon(user_id) is not None:
                break
    coupon = get_coupon(user_id)
    assert coupon is not None
    return coupon.model_copy(update={"already_claimed": False})


def upgrade_coupon(user_id: int, discount_pct: int) -> None:
    """Lift the shopper's one coupon (same code) to a higher percentage. Never lowers it."""
    with connect(write=True) as con:
        con.execute(
            "UPDATE coupons SET discount_pct = ? WHERE user_id = ? AND discount_pct < ?",
            (int(discount_pct), int(user_id), int(discount_pct)),
        )


# ------------------------------------------------------------------ hidden friends (Problem 9)


@dataclass(frozen=True)
class FindRow:
    season: str
    character: str
    source: str  # found | referral
    created_at: str


def list_finds(user_id: int) -> list[FindRow]:
    with connect() as con:
        rows = con.execute(
            "SELECT season, character, source, created_at FROM egg_finds WHERE user_id = ? ORDER BY id",
            (int(user_id),),
        ).fetchall()
    return [FindRow(r["season"], r["character"], r["source"], _iso_utc(r["created_at"])) for r in rows]


def add_find(user_id: int, season: str, character: str) -> bool:
    """Record a find. Returns False when this friend was already found this season."""
    try:
        with connect(write=True) as con:
            con.execute(
                "INSERT INTO egg_finds (user_id, season, character, source) VALUES (?, ?, ?, 'found')",
                (int(user_id), season, character),
            )
    except sqlite3.IntegrityError:
        return False
    return True


def add_referral_credit(referrer_id: int, referred_id: int, season: str, cap: int) -> bool:
    """One credit for the referrer when a new account used their code, up to `cap` credits."""
    with connect(write=True) as con:
        have = con.execute(
            "SELECT COUNT(*) AS n FROM egg_finds WHERE user_id = ? AND source = 'referral'", (int(referrer_id),)
        ).fetchone()["n"]
        if int(have) >= cap:
            return False
        try:
            con.execute(
                "INSERT INTO egg_finds (user_id, season, character, source, referred_user_id) VALUES (?, ?, 'referral', 'referral', ?)",
                (int(referrer_id), season, int(referred_id)),
            )
        except sqlite3.IntegrityError:
            return False  # that new account was already credited
    return True


def _reward(row: sqlite3.Row) -> Reward:
    return Reward(
        kind=row["kind"],
        code=row["code"],
        max_value_usd=int(row["max_value_usd"]),
        created_at=_iso_utc(row["created_at"]),
        redeemed_at=_iso_utc(row["redeemed_at"]) if row["redeemed_at"] else None,
    )


def list_rewards(user_id: int) -> list[Reward]:
    with connect() as con:
        rows = con.execute("SELECT * FROM rewards WHERE user_id = ? ORDER BY id", (int(user_id),)).fetchall()
    return [_reward(r) for r in rows]


def grant_reward(user_id: int, kind: str, code: str, max_value_usd: int) -> Reward | None:
    """Grant one reward of a kind per shopper. Returns None when they already have it."""
    try:
        with connect(write=True) as con:
            con.execute(
                "INSERT INTO rewards (user_id, kind, code, max_value_usd) VALUES (?, ?, ?, ?)",
                (int(user_id), kind, code, int(max_value_usd)),
            )
    except sqlite3.IntegrityError:
        return None
    with connect() as con:
        row = con.execute("SELECT * FROM rewards WHERE user_id = ? AND kind = ?", (int(user_id), kind)).fetchone()
    return _reward(row) if row else None


# ------------------------------------------------------------------ restock requests (Problem 9)


@dataclass(frozen=True)
class RestockRow:
    id: int
    user_id: int
    product_id: str
    product_name: str
    size: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AdminRestockRow:
    id: int
    product_id: str
    product_name: str
    size: str
    user_name: str
    user_email: str
    created_at: str


_RESTOCK_SELECT = """
    SELECT r.id, r.user_id, r.product_id, c.name AS product_name, r.size, r.status, r.created_at, r.updated_at
    FROM restock_requests r JOIN catalogue c ON c.product_id = r.product_id
"""


def _restock(row: sqlite3.Row | None) -> RestockRow | None:
    if row is None:
        return None
    return RestockRow(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        product_id=row["product_id"],
        product_name=row["product_name"],
        size=row["size"],
        status=row["status"],
        created_at=_iso_utc(row["created_at"]),
        updated_at=_iso_utc(row["updated_at"]),
    )


def get_restock_request(request_id: int) -> RestockRow | None:
    with connect() as con:
        return _restock(con.execute(_RESTOCK_SELECT + " WHERE r.id = ?", (int(request_id),)).fetchone())


def list_restock_requests(user_id: int) -> list[RestockRow]:
    with connect() as con:
        rows = con.execute(_RESTOCK_SELECT + " WHERE r.user_id = ? ORDER BY r.id DESC", (int(user_id),)).fetchall()
    return [r for r in (_restock(x) for x in rows) if r is not None]


def count_open_restock_requests(user_id: int) -> int:
    with connect() as con:
        return int(
            con.execute(
                "SELECT COUNT(*) AS n FROM restock_requests WHERE user_id = ? AND status = 'open'", (int(user_id),)
            ).fetchone()["n"]
        )


def add_restock_request(user_id: int, product_id: str, size: str) -> tuple[RestockRow, bool]:
    """Open a request, or return the already-open one for the same product and size (created=False)."""
    created = True
    try:
        with connect(write=True) as con:
            con.execute(
                "INSERT INTO restock_requests (user_id, product_id, size) VALUES (?, ?, ?)",
                (int(user_id), product_id, size),
            )
    except sqlite3.IntegrityError:
        created = False
    with connect() as con:
        row = con.execute(
            _RESTOCK_SELECT + " WHERE r.user_id = ? AND r.product_id = ? AND r.size = ? AND r.status = 'open'",
            (int(user_id), product_id, size),
        ).fetchone()
    found = _restock(row)
    assert found is not None
    return found, created


def cancel_restock_request(user_id: int, request_id: int) -> RestockRow | None:
    """The shopper withdraws their own open request. Other shoppers' rows are never touched."""
    with connect(write=True) as con:
        con.execute(
            "UPDATE restock_requests SET status = 'cancelled', updated_at = datetime('now') "
            "WHERE id = ? AND user_id = ? AND status = 'open'",
            (int(request_id), int(user_id)),
        )
    found = get_restock_request(request_id)
    return found if found and found.user_id == int(user_id) else None


def open_restock_queue() -> list[AdminRestockRow]:
    """Every open request with who asked, for the admin's ordering list (a documented PII use)."""
    with connect() as con:
        rows = con.execute(
            """
            SELECT r.id, r.product_id, c.name AS product_name, r.size, r.created_at,
                   u.name AS user_name, u.email AS user_email
            FROM restock_requests r
            JOIN catalogue c ON c.product_id = r.product_id
            JOIN users u ON u.id = r.user_id
            WHERE r.status = 'open'
            ORDER BY c.name, r.size, r.id
            """
        ).fetchall()
    return [
        AdminRestockRow(
            id=int(r["id"]),
            product_id=r["product_id"],
            product_name=r["product_name"],
            size=r["size"],
            user_name=r["user_name"],
            user_email=r["user_email"],
            created_at=_iso_utc(r["created_at"]),
        )
        for r in rows
    ]


def mark_restock_ordered(request_id: int) -> RestockRow | None:
    with connect(write=True) as con:
        con.execute(
            "UPDATE restock_requests SET status = 'ordered', updated_at = datetime('now') WHERE id = ? AND status = 'open'",
            (int(request_id),),
        )
    return get_restock_request(request_id)
