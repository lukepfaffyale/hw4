# Logical model: Campus Customs shop + chatbot

Exact tables, columns, keys and types in `data/campus_customs.db` (SQLite, shipped with the assignment, profiled 2026-10-16), plus how the back end reaches them. The API-to-table mapping section is filled in as endpoints are built in later problems.

## Database

- **Engine:** SQLite 3, single file `data/campus_customs.db` (172 KB). Assignment-specified; the course default (Supabase) is not used here, recorded as a deliberate exception in `docs/governance.md`.
- **Access path:** only `backend/db.py` opens the file. Routes call typed repository functions in `db.py`; no SQL in routes, no string-built queries, parameters only.
- **Not in Git:** the file and `data/products/` are gitignored (assignment rule). `backend/data/schema.sql` will hold the DDL so the structure is versioned even though the data is not.

## Tables

### `catalogue` (102 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `product_id` | TEXT | no | PK | Slug, e.g. `basic-hoodie-big-yale`. Also the image file stem. |
| `name` | TEXT | no | | Title-cased slug, e.g. "Basic Hoodie Big Yale". Unique in practice. |
| `garment_type` | TEXT | no | | Free text, 22 distinct values, inconsistent case. |
| `description` | TEXT | no | | One or two sentences, 93 to 184 chars. |
| `colors` | TEXT (JSON array of strings) | no | | 0 to 5 colours; 3 products have `[]`. |
| `search_tags` | TEXT (JSON array of strings) | no | | 4 to 12 tags; "Yale" on 88 of 102. |
| `image_file_path` | TEXT | no | | Always `products/<product_id>.jpg`, relative to `data/`. All 102 files present. |
| `price` | REAL | no | | USD. Seven price points: 32, 45, 58, 68, 72, 88, 98. |

### `inventory` (612 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `product_id` | TEXT | no | FK -> `catalogue.product_id` | No orphans. |
| `size` | TEXT | no | UNIQUE with `product_id` | Exactly `XS, S, M, L, XL, XXL`; six rows per product. |
| `quantity` | INTEGER | no | | 0 to 25. 145 rows are 0 (sold out in that size). Per-product totals 9 to 116. |

### `users` (3 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `name` | TEXT | no | | Equals `first_name + ' ' + last_name` on all rows. |
| `email` | TEXT | no | UNIQUE | Lower-case in shipped rows. |
| `password_hash` | TEXT | no | | `pbkdf2_sha256$<hex salt>$<hex sha256>`; no iteration count stored. |
| `created_at` | TEXT | no | | Default `datetime('now')`, format `YYYY-MM-DD HH:MM:SS`, UTC, no zone suffix. |
| `first_name` | TEXT | yes | | Added later via ALTER TABLE; filled on all rows. |
| `last_name` | TEXT | yes | | Same. |
| `auth_provider` | TEXT | no (default `password`) | | Added by the app 2026-10-18: `password`, `google`, `github`. |
| `provider_user_id` | TEXT | yes | | Added by the app 2026-10-18: the provider's user id for social accounts. |

Also added by the app: index `idx_chat_messages_user` on `chat_messages(user_id, created_at)`. DDL in `backend/data/schema.sql`; applied idempotently at startup by `db.ensure_schema()`.

### `coupons` (added by the app 2026-10-19)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `user_id` | INTEGER | no | FK -> `users.id`, UNIQUE | one coupon per shopper, enforced by the database |
| `code` | TEXT | no | UNIQUE | `TOTORO10-XXXX` / `LABUBU10-XXXX` |
| `discount_pct` | INTEGER | no (default 10) | | |
| `scope` | TEXT | no (default `one_item`) | | good for one item |
| `found_character` | TEXT | no | | `totoro` or `labubu` |
| `created_at` | TEXT | no | | UTC |
| `redeemed_at` | TEXT | yes | | one-time use; set by a future checkout |

Since Problem 9 `code` is `<FRIEND>10-XXXX` (first word of the friend key) and `discount_pct` is lifted to 15 in place when the season's set is complete.

### `users` additions (Problem 9, 2026-10-19)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `referral_code` | TEXT | yes (backfilled at startup) | UNIQUE index `idx_users_referral_code` | 8 characters from an unambiguous alphabet |
| `referred_by` | INTEGER | yes | FK -> `users.id` ON DELETE SET NULL | the referrer, from the code typed at signup |

### `egg_finds` (added by the app 2026-10-19)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `user_id` | INTEGER | no | FK -> `users.id` | |
| `season` | TEXT | no | | season key from `hunt.py` |
| `character` | TEXT | no | | friend key, or `referral` |
| `source` | TEXT | no (default `found`) | | `found` or `referral` |
| `referred_user_id` | INTEGER | yes | FK -> `users.id` ON DELETE SET NULL | |
| `created_at` | TEXT | no | | UTC |

Partial unique indexes: `idx_egg_finds_found (user_id, season, character) WHERE source = 'found'` (a friend counts once per season) and `idx_egg_finds_referred (referred_user_id) WHERE referred_user_id IS NOT NULL` (a new account credits one referrer once).

### `rewards` (added by the app 2026-10-19)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `user_id` | INTEGER | no | FK -> `users.id`, UNIQUE with `kind` | one reward per kind per shopper |
| `kind` | TEXT | no | | `free_item` |
| `code` | TEXT | no | UNIQUE | `FREEITEM-XXXXXX` |
| `max_value_usd` | INTEGER | no (default 100) | | |
| `created_at` | TEXT | no | | UTC |
| `redeemed_at` | TEXT | yes | | |

### `restock_requests` (added by the app 2026-10-19)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `user_id` | INTEGER | no | FK -> `users.id` | |
| `product_id` | TEXT | no | FK -> `catalogue.product_id` | |
| `size` | TEXT | no | | XS to XXL, verified at zero stock before insert |
| `status` | TEXT | no (default `open`) | | `open`, `ordered`, `cancelled` |
| `created_at`, `updated_at` | TEXT | no | | UTC |

Partial unique index `idx_restock_open (user_id, product_id, size) WHERE status = 'open'`: one open request per shopper per size, and a cancelled one can be re-filed.

### `chat_messages` (22 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | INTEGER | no | PK autoincrement | |
| `user_id` | INTEGER | no | FK -> `users.id` | No index; add one on `(user_id, created_at)` when we write the schema. |
| `role` | TEXT | no | | `user` or `assistant` only. |
| `content` | TEXT | no | | 2 to 643 chars. Free text from the shopper or the bot. |
| `products_json` | TEXT (JSON array) | yes | | NULL on every `user` row, set on every `assistant` row (may be `[]`). Each item is a product snapshot: all `catalogue` columns plus `image_url`, `inventory` (list of `{size, quantity}`) and `total_stock`. |
| `created_at` | TEXT | no | | Same default and format as `users.created_at`. |

`sqlite_sequence` is SQLite's own autoincrement bookkeeping, not an app table.

## Keys and relationships

```
catalogue.product_id  1 ──< inventory.product_id         (6 rows per product)
catalogue.product_id  1 ──< restock_requests.product_id  (0..n per product)
users.id              1 ──< chat_messages.user_id         (0..n per user)
users.id              1 ──  coupons.user_id               (0..1 per user)
users.id              1 ──< egg_finds.user_id             (0..n per user; one per season per friend)
users.id              1 ──< egg_finds.referred_user_id    (0..1 credit per new account)
users.id              1 ──< rewards.user_id               (0..1 per kind)
users.id              1 ──< restock_requests.user_id      (0..n per user; at most 10 open)
users.id              1 ──< users.referred_by             (who invited whom)
chat_messages.products_json  ──  embedded catalogue snapshots (no FK; by design, keeps history stable)
```

Foreign keys are declared but SQLite only enforces them with `PRAGMA foreign_keys = ON`; `db.py` sets it on every connection.

## Derived fields the app computes (not stored)

| Derived | From | Used for |
|---|---|---|
| `category` | normalised `garment_type` | filters and bot search: hoodie, crewneck, t-shirt, quarter-zip, jacket, performance, other |
| `image_url` | `image_file_path` | `/media/products/<id>.jpg` served by the back end; file name never from the client |
| `sizes_in_stock` / `total_stock` | `inventory` | cards, honest stock answers |
| `display_name` | `name` | same as `name` for now |

## API endpoint -> Pydantic model -> table

Built in Problem 4 (read-only):

| Endpoint | Request model | Response model | Tables |
|---|---|---|---|
| `GET /health` | none | `Health` | none |
| `GET /products` | `ProductQuery` (q, category, max_price, in_stock, sort; unknown params rejected) | `ProductList` of `ProductSummary` (with `sizes_in_stock` since Problem 9) | catalogue, inventory (sum and sizes per product) |
| `GET /products/{product_id}` | path id, pattern-checked | `ProductDetail` (+ `StockLevel[]`) | catalogue, inventory |
| `GET /media/products/{product_id}` | path id, pattern-checked | JPEG | catalogue (`image_file_path`), file under `data/products/` |

Built in Problem 4 (accounts):

| Endpoint | Request model | Response model | Tables |
|---|---|---|---|
| `GET /auth/password-policy` | none | `PasswordPolicy` | none |
| `POST /auth/signup` | `SignupRequest` (extra forbid; strict password policy; confirm must match) | `AuthResponse` (token + `UserPublic`) | users (insert; hash only) |
| `POST /auth/login` | `LoginRequest` (extra forbid) | `AuthResponse` | users (read; constant-time verify) |
| `POST /auth/social` | `SocialLoginRequest` (Supabase access token) | `AuthResponse` | users (find by provider id, link by verified email, or insert with `!social`) |
| `GET /me` | Bearer token | `UserPublic` | users (own row) |
| `DELETE /me` | Bearer token | `DeleteMeResponse` | chat_messages + coupons + egg_finds + rewards + restock_requests + users (own rows, one transaction; referral links to others set to NULL) |

The Problem 4 coupon endpoints (`POST/GET /me/coupon`) were replaced in Problem 9 by the hunt endpoints below; the coupon is now earned by finds and read from `GET /me/hunt`.

All auth endpoints are rate-limited (per client address and per email). Validation errors return field and message only, never the submitted value.

Built in Problem 5 (agent):

| Endpoint | Request model | Response model | Tables |
|---|---|---|---|
| `POST /chat` | `ChatRequest` (message ≤ 1000 chars, guest `history` ≤ 12 turns; extra forbid), optional Bearer token | `ChatResponse` (reply, product cards, stop reason, flagged) | catalogue + inventory read by tools; chat_messages written for signed-in shoppers only (cleaned text, `products_json` of the cards) |
| `GET /me/activity` | Bearer token | `ActivityResponse` | chat_messages (own rows, oldest first) |
| `DELETE /me/activity` | Bearer token | `DeleteActivityResponse` | chat_messages (own rows) |

Built in Problem 9 (usability):

| Endpoint | Request model | Response model | Tables |
|---|---|---|---|
| `GET /hunt` | none | `HuntProgram` (seasons, friends, riddles, milestones) | none (defined in `hunt.py`) |
| `GET /me/hunt` | Bearer token | `HuntProgress` | egg_finds, coupons, rewards, users (own rows) |
| `POST /me/hunt/finds` | Bearer token + `FindRequest` (season, character; extra forbid) | `HuntProgress` with `unlocked` | egg_finds (insert if new); coupons (insert at 3, lift at full set); rewards (insert at 10) |
| `POST /auth/signup` (extended) | `SignupRequest` + optional `referral_code` | `AuthResponse` | users (`referred_by`); egg_finds (referral credit, capped at 3) |
| `GET /me/restock-requests` | Bearer token | `RestockList` | restock_requests + catalogue (own rows) |
| `POST /me/restock-requests` | Bearer token + `RestockCreateRequest` (product_id, size; extra forbid) | `RestockStatusResponse` (201) or 409 | inventory (verify zero), restock_requests (insert or reuse open row) |
| `DELETE /me/restock-requests/{id}` | Bearer token | `RestockStatusResponse` | restock_requests (own open row -> cancelled) |
| `GET /admin/restock-requests` | Bearer token of an `ADMIN_EMAILS` account | `AdminRestockQueue` (groups with requester name and email) | restock_requests + catalogue + users |
| `GET /admin/restock-requests.csv` | same | CSV | same |
| `POST /admin/restock-requests/{id}/ordered` | same | `RestockStatusResponse` | restock_requests (open -> ordered) |
| `POST /chat` (extended) | `ChatRequest` | `ChatResponse` + `go_to: PageLink` (validated) | as before; `request_restock` may insert into restock_requests for the signed-in shopper; `hiding_clue` reads the shopper's own egg_finds |

The agent's tools (`tools.py`) read `catalogue` and `inventory` through `db.py`; `hiding_clue` reads the signed-in shopper's own `egg_finds`; `request_restock` is the one write, into `restock_requests`, for the signed-in shopper only and only for a size the database shows at zero. No tool reads `users`, `coupons` or any other shopper's rows.

## How the pieces connect

`backend/db.py` opens the SQLite file and exposes typed repository functions. `backend/models.py` mirrors each table as a Pydantic model and defines the request and response schemas above. `backend/tools.py` wraps the read-only product and stock lookups as agent tools that call `db.py`. `backend/main.py` exposes the endpoints. The front end calls them through one typed API client in `frontend/src/api.ts`.
