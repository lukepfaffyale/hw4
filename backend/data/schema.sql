-- Campus Customs schema. The data itself ships in the course pack (data/campus_customs.db) and is
-- never committed. Tables 1-4 are exactly as shipped; section 5 is what the app adds at startup
-- (backend/db.py ensure_schema, idempotent). Changes are logged in docs/data/CHANGELOG.md.

-- 1. Products
CREATE TABLE IF NOT EXISTS catalogue (
    product_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    garment_type    TEXT NOT NULL,
    description     TEXT NOT NULL,
    colors          TEXT NOT NULL,          -- JSON array of strings
    search_tags     TEXT NOT NULL,          -- JSON array of strings
    image_file_path TEXT NOT NULL,          -- products/<product_id>.jpg, relative to data/
    price           REAL NOT NULL
);

-- 2. Stock by size
CREATE TABLE IF NOT EXISTS inventory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    size       TEXT NOT NULL,               -- XS, S, M, L, XL, XXL
    quantity   INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES catalogue(product_id),
    UNIQUE (product_id, size)
);

-- 3. Shoppers (PII: name, first_name, last_name, email; password_hash is a secret, never plaintext)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,     -- stored lower-cased
    password_hash TEXT NOT NULL,            -- pbkdf2_sha256$salt$hex (seeded) | $2b$12$... (bcrypt) | !social
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    first_name    TEXT,
    last_name     TEXT
);

-- 4. Chat turns (PII: content is free text; user_id links to a person)
CREATE TABLE IF NOT EXISTS chat_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    role          TEXT NOT NULL,            -- user | assistant
    content       TEXT NOT NULL,
    products_json TEXT,                     -- JSON snapshot of products shown with an assistant turn
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 5. Added by the app (Problem 4, 2026-10-18)
-- ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'password';  -- password | google | github
-- ALTER TABLE users ADD COLUMN provider_user_id TEXT;                            -- the provider's stable user id
CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, created_at);

-- 6. Easter-egg coupon (Problem 4 follow-up, 2026-10-19): one per shopper, one item, one time
CREATE TABLE IF NOT EXISTS coupons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE,     -- one coupon per shopper
    code            TEXT NOT NULL UNIQUE,        -- TOTORO10-XXXX | LABUBU10-XXXX
    discount_pct    INTEGER NOT NULL DEFAULT 10,
    scope           TEXT NOT NULL DEFAULT 'one_item',
    found_character TEXT NOT NULL,               -- totoro | labubu
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    redeemed_at     TEXT,                        -- set once, by a future checkout
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 7. Problem 9 (2026-10-19): hidden-friends collection, referrals, bigger rewards, restock requests.
-- ALTER TABLE users ADD COLUMN referral_code TEXT;                                            -- 8 chars, unique, not PII
-- ALTER TABLE users ADD COLUMN referred_by INTEGER REFERENCES users(id) ON DELETE SET NULL;  -- who invited them
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

CREATE TABLE IF NOT EXISTS egg_finds (            -- one row per friend found (or referral credit) per shopper
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    season           TEXT NOT NULL,                -- halloween | thanksgiving | winter (defined in hunt.py)
    character        TEXT NOT NULL,                -- friend key such as totoro-witch, or 'referral'
    source           TEXT NOT NULL DEFAULT 'found', -- found | referral
    referred_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- the account that used the code
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_egg_finds_found ON egg_finds(user_id, season, character) WHERE source = 'found';
CREATE UNIQUE INDEX IF NOT EXISTS idx_egg_finds_referred ON egg_finds(referred_user_id) WHERE referred_user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS rewards (              -- the free item at ten finds; one per kind per shopper
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    kind          TEXT NOT NULL,                   -- free_item
    code          TEXT NOT NULL UNIQUE,            -- FREEITEM-XXXXXX
    max_value_usd INTEGER NOT NULL DEFAULT 100,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    redeemed_at   TEXT,
    UNIQUE (user_id, kind)
);

CREATE TABLE IF NOT EXISTS restock_requests (     -- "reorder this size for me", filed from an item page or the chat
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    product_id TEXT NOT NULL REFERENCES catalogue(product_id),
    size       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open',       -- open | ordered | cancelled
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_restock_open ON restock_requests(user_id, product_id, size) WHERE status = 'open';
