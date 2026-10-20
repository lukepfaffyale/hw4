# Data dictionary: Campus Customs shop + chatbot

Every column the app reads or writes, classified PII or not PII before any data is collected. Source: `data/campus_customs.db` as shipped (2026-10-16). Retention applies to rows the app creates; the shipped rows belong to the course data pack.

PII rule used: a name, email, free text a person typed, or anything that identifies a person is PII. Product and stock data is not.

## `catalogue` (shop-owned, no PII)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| product_id | text | data pack | no | stable key for cards, links, chat snapshots | life of catalogue |
| name | text | data pack | no | what the shopper sees and the bot says | life of catalogue |
| garment_type | text | data pack | no | filtering and bot search | life of catalogue |
| description | text | data pack | no | product copy on cards and in bot answers | life of catalogue |
| colors | JSON list | data pack | no | colour questions ("in pink?") | life of catalogue |
| search_tags | JSON list | data pack | no | keyword search ("bulldog", "Handsome Dan") | life of catalogue |
| image_file_path | text | data pack | no | serve the product photo | life of catalogue |
| price | real | data pack | no | honest price answers, sorting | life of catalogue |

## `inventory` (shop-owned, no PII)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | data pack | no | row key | life of catalogue |
| product_id | text | data pack | no | links stock to product | life of catalogue |
| size | text | data pack | no | per-size availability | life of catalogue |
| quantity | int | data pack | no | honest stock answers | life of catalogue |

## `users` (PII)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no (internal id) | key for scoping a shopper's own rows | until account deleted |
| name | text | shopper types at signup | **yes** | greeting, "do you remember my name?" | until account deleted |
| first_name | text | shopper types at signup | **yes** | greeting | until account deleted |
| last_name | text | shopper types at signup | **yes** | kept for parity with shipped rows | until account deleted |
| email | text | shopper types at signup | **yes** | login identity, unique | until account deleted |
| password_hash | text | derived by back end | no plaintext ever; treat as secret | login verification only; `!social` marker for social accounts | until account deleted |
| created_at | text (UTC) | app | no | account age ("member since") | until account deleted |
| auth_provider | text | app (added 2026-10-18) | no | which sign-in path the account uses: password, google, github | until account deleted |
| provider_user_id | text, nullable | social provider via Supabase (added 2026-10-18) | **yes** (third-party identifier for a person) | find the account on the next social sign-in | until account deleted |

Notes: the password itself is never stored, logged, returned, or sent to a model. New accounts hash with bcrypt (cost 12, per-password salt inside the hash); shipped rows use PBKDF2-HMAC-SHA256 (120,000 iterations, salt as raw string, hex digest) and are verified with that scheme; `PASSWORD_SCHEME=pbkdf2` makes new accounts use the course format. Email is stored lower-cased. Validation errors never echo the submitted password. Social accounts hold no password at all.

**Session token (not a column).** Signup and login return a signed, expiring token (user id, expiry, nonce; HMAC-SHA256 under `SESSION_SECRET`). The server stores nothing for it; the browser keeps it in `localStorage` for seven days or until sign-out. It identifies a person while valid, so it is treated as sensitive: never logged, never in a URL.

**Social sign-in (Supabase Auth).** When configured, Supabase also stores the social user's email, provider id and basic profile on its side, under the provider's default scopes. Recorded in `docs/governance.md`.

## `chat_messages` (PII: free text and link to a person)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no | row key | until the shopper deletes, or account deleted |
| user_id | int | app | **yes** (links to a person) | scope history to its owner | same |
| role | text | app | no | render user vs bot turns | same |
| content | text | shopper types / bot writes | **yes** (free text may contain identity) | chat history, bot memory | same |
| products_json | JSON | app | no | re-show the cards the bot showed | same |
| created_at | text (UTC) | app | no | ordering, activity view | same |

Notes: `content` passes through the prompt guard before it reaches the model or the database, so stored text is the cleaned text. The audit log (`backend/output/audit.jsonl`) records a random run id, cleaned text and product ids, never email, name or user id. Rows are written only for signed-in shoppers; guests' turns are never stored. The model receives the cleaned message, the shopper's recent turns, and, for a signed-in shopper, their first name (PII, sent so the assistant can greet them; recorded here on purpose). Last name and email reach the model only when the shopper asks who they are (the `who_am_i` tool), and the audit log redacts email addresses. Page context (the current route and the product id on screen) is sent with each message, used for that turn, and not stored (Problem 8). Since Problem 9 the on-screen product's stock by size (shop data, not PII) is read from the database and placed in that turn's instructions so the answer needs no tool round trip.

## `coupons` (added 2026-10-19; one row per shopper)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no | row key | until account deleted |
| user_id | int, UNIQUE | app | **yes** (links to a person) | one coupon per shopper | until account deleted |
| code | text, UNIQUE | app | no | the 10% code shown to the shopper | until account deleted |
| discount_pct | int | app (10, lifted to 15 when a season's set is complete) | no | discount size | until account deleted |
| scope | text | app (always `one_item`) | no | the coupon applies to a single item | until account deleted |
| found_character | text | app (friend key such as `soot-skeleton`; older rows `totoro` or `labubu`) | no | which hidden friend earned it | until account deleted |
| created_at | text (UTC) | app | no | when it was claimed | until account deleted |
| redeemed_at | text (UTC), nullable | app (future checkout) | no | one-time use: set when redeemed | until account deleted |

Notes: since Problem 9 the coupon is earned by three finds in a season (see `egg_finds`), not by a single tap. A guest's finds are held in the browser's `localStorage` (`cc-hunt-guest`: season and friend keys only) until they sign in. Codes are class-project codes and say so in the UI.

## `users` columns added 2026-10-19 (Problem 9)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| referral_code | text, UNIQUE | app (8 random characters) | no | the code a shopper gives a friend; printed on their Account page and in the invite link `/create-account?ref=CODE` | until account deleted |
| referred_by | int, nullable | app (looked up from the code typed at signup) | **yes** (links two people) | credit the referrer; set to NULL if the referrer deletes their account | until either account is deleted |

## `egg_finds` (added 2026-10-19; one row per friend found, or per referral credit)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no | row key | until account deleted |
| user_id | int | app (session) | **yes** (links to a person) | whose find it is | until account deleted |
| season | text | app (`hunt.py`) | no | which seasonal set | until account deleted |
| character | text | app (friend key, or `referral`) | no | which friend; unique per shopper per season for real finds | until account deleted |
| source | text | app (`found` or `referral`) | no | real find versus referral credit (credits are capped at three) | until account deleted |
| referred_user_id | int, nullable | app | **yes** (links to a person) | which new account used the code; one credit per new account; NULL when that account is deleted | until either account is deleted |
| created_at | text (UTC) | app | no | the find date shown in the tray | until account deleted |

Notes: the server decides what finds earn; the browser only reports a tap. `GET /hunt` (the programme) carries no shopper data; `GET /me/hunt` returns only the signed-in shopper's own rows.

## `rewards` (added 2026-10-19; the free-item voucher for a complete set)

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no | row key | until account deleted |
| user_id | int | app (session) | **yes** (links to a person) | whose reward | until account deleted |
| kind | text | app (`free_item`), unique per shopper | no | one reward of each kind per shopper | until account deleted |
| code | text, UNIQUE | app | no | the `FREEITEM-XXXXXX` code shown on the Account page | until account deleted |
| max_value_usd | int | app (100) | no | the cap printed with the code; the voucher terms (with purchase, in-stock only, while supplies last) are constant text in `models.FREE_ITEM_TERMS`, not stored | until account deleted |
| created_at | text (UTC) | app | no | when earned | until account deleted |
| redeemed_at | text (UTC), nullable | app (future checkout) | no | one-time use | until account deleted |

## `restock_requests` (added 2026-10-19; "reorder this size for me")

| Column | Type | Source | PII | Purpose | Retention |
|---|---|---|---|---|---|
| id | int | app | no | row key | until account deleted or cancelled by the shopper |
| user_id | int | app (session) | **yes** (links to a person) | whose request; staff see the shopper's name and email next to it so they can tell them when stock arrives | until account deleted |
| product_id | text | app (verified against `catalogue`) | no | what to order | until account deleted |
| size | text | app (verified at zero stock in `inventory`) | no | which size | until account deleted |
| status | text | app (`open`, `ordered`, `cancelled`) | no | the shop's progress and the shopper's cancel | until account deleted |
| created_at, updated_at | text (UTC) | app | no | ordering the queue; when it changed | until account deleted |

Notes: the only write the chat agent can make. The same rule set serves the item page button. The staff view (`/admin/restock-requests`, and its CSV) is the one place name and email are shown to someone other than the shopper, limited to accounts listed in `ADMIN_EMAILS`, for the purpose above; it is recorded in `docs/governance.md`.

## Columns deliberately not collected

Phone, address, payment details, device id, IP address, browsing history. None has a purpose in this assignment. Adding any of them requires a new row here and a note in `docs/governance.md` first.
