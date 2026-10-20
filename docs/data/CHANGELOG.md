# Schema changelog

| Date | Change | Reason |
|---|---|---|
| 2026-10-16 | Documented the shipped schema as-is: `catalogue`, `inventory`, `users`, `chat_messages`. No structural change. | Problem 2, database analysis. |
| 2026-10-18 | No schema change. API now derives `category`, `short_description`, `image_url`, `total_stock`, per-size `status` and `sizes_in_stock` at read time (see `logical_model.md`, derived fields). | Problem 3 (continued), read-only products API. |
| 2026-10-18 | `users`: added `auth_provider TEXT NOT NULL DEFAULT 'password'` and `provider_user_id TEXT`. Added index `idx_chat_messages_user (user_id, created_at)`. Applied by `db.ensure_schema()` at startup; DDL in `backend/data/schema.sql`. Existing rows untouched (hashes left as shipped). | Problem 4, accounts with social sign-in. |
| 2026-10-19 | New table `coupons` (id, user_id UNIQUE FK users, code UNIQUE, discount_pct, scope, found_character, created_at, redeemed_at). | Problem 4 follow-up: Easter-egg coupon, one per shopper, one item, once. |
| 2026-10-19 | `users`: added `referral_code TEXT` (unique index) and `referred_by INTEGER REFERENCES users(id) ON DELETE SET NULL`; new tables `egg_finds`, `rewards`, `restock_requests` with partial unique indexes (`idx_egg_finds_found`, `idx_egg_finds_referred`, `idx_restock_open`). Applied by `db.ensure_schema()`; DDL in `backend/data/schema.sql` section 7. `coupons.discount_pct` may now be lifted from 10 to 15 in place. | Problem 9: hidden-friends collection with referrals and a free-item reward; restock requests from the chat and the item page with a staff queue. |
