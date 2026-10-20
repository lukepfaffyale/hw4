# Usability improvements (Problem 9)

Four improvements on top of the working shop: two on the front end (look better, easier to use) and two on the agent and back end (better, more accurate, safer, faster answers). Each one says what we added, why it helps a Campus Customs shopper or the business, and where to see it in the running app. We chose them after a short friction audit, which comes first.

Everything below is live at http://localhost:5173 with the back end on port 8000. Screenshots are in `docs/screenshots/p9-*.jpg` (and `p10-*.jpg` after the Problem 10 polish); the tests are in `backend/tests/test_usability.py` (16 new, 66 passing in all).

---

## 0. Where shoppers lose time: a quick friction audit

Measured on 2026-10-19 before choosing the improvements (API timings through FastAPI's test client, chat timings from `backend/output/audit.jsonl`, image sizes from `data/products/`, bundle sizes from `npm run build`).

| Friction point | What we measured | Verdict |
|---|---|---|
| Page and API load time | `GET /products` (102 items) 3.6 ms, one item 3.1 ms, product list 42 KB; images average 35 KB (max 95 KB, 3.7 MB for all 102, lazy-loaded); JS bundle 434 KB (130 KB gzipped) | Not the bottleneck. Left alone. |
| Chat turn time | Median 4.6 s for a turn with one tool call, 11.8 s for a turn with three. Each extra model round trip costs roughly 3 to 4 s. | The lever is the number of round trips, not the server. See improvement 4. |
| Clicks to learn whether your size exists | Products page card says only "In stock"; the shopper opens the item, scrolls to the table, goes back: 2 clicks plus a scroll per item, repeated per item | Fixed by size chips on every card (improvement 2). |
| Narrowing 102 products | Only category and a text search in the UI, although the API already accepted a price cap and in-stock-only; no sort; filters not in the URL (no sharing, back button lost them) | Fixed by URL-backed filters and sort (improvement 2). |
| A sold-out size was a dead end | The assistant said "👻 Sold out in M" and stopped; the item page offered nothing | Fixed by alternatives and restock requests (improvements 3 and 4). |
| Getting from a chat answer to the page | After a category question the shopper still had to click "Show these on the Products page" or set filters by hand | Fixed by the assistant's page links (improvement 4). |
| Finding a hidden friend as a guest | Find, then sign in, then land on the Account page for the claim to finish: three steps with a pending flag in the browser | Guest finds are now saved locally and banked automatically at sign-in (improvement 1). |

Measured again after the build (live run on 2026-10-19, same audit log): "do you have this in XS?" on an item page took one tool call (the new alternatives lookup) and 7.0 s; the stock answer itself came from the page note with no stock lookup. "Any clue where the hidden friends are?" took one tool call and 4.1 s. "Take me to the hoodies under $50, cheapest first" took one search call, 5.6 s, and moved the page itself.

---

## 1. Front end: Hidden friends you collect (a 31-day set, a chase, rewards, referrals)

**What we added**

- The two random Easter eggs became a collection. The cast is seven characters, Totoro, Chu Totoro, Chibi Totoro, Catbus, Labubu, a Soot Sprite and No-Face, dressed in trick-or-treat costumes: witch, ghost, zombie, skeleton, vampire, mummy, pumpkin and devil. The Halloween set is **31 friends, one for each day of October**: day 1 is Witch Totoro, day 2 Ghost Chu Totoro, day 3 Zombie Chibi Totoro, and so on, with character and costume both advancing each day so no pairing repeats. A friend becomes findable on its day and stays findable until the set ends (`HUNT_DATE` in `.env` pins the date for a demo). Costumes are drawn as overlays on each character in `frontend/src/eggs/characters.tsx`. Thanksgiving and Winter sets are defined in `backend/hunt.py` and listed as "coming up"; they switch on when their art is ready, so the site never shows a set it cannot draw.
- The chase: every friend has a home page (Home, Products, About, any item page, rotating day by day) where it always hides until found, in a text-free spot (footer end, Halloween scene, a product photo corner, or the wide-screen gutter). The earliest friend not yet found is the one that shows, so the chase runs in day order through the whole site; unfound friends also stray onto other pages about a third of the time. Each find's dialog gives the riddle for the next friend, and the chat assistant repeats the riddle on request (`hiding_clue` tool).
- Rewards, all decided on the server (`POST /me/hunt/finds`), never in the browser:
  - **3 finds** in a season earn the shopper's single coupon, **10% off one item**.
  - **10 finds** across seasons lift that same coupon to **15%**. Friend referrals count as finds, up to three: every account has an 8-character referral code and an invite link, and the Create Account page takes the code (prefilled from the link).
  - **The whole set** (all 31) earns the **free-item voucher**: a free item with the purchase of another item, up to $100 in value, in-stock items only, while supplies last.
- The Account page shows the collection: a 31-slot tray with the friends found, silhouettes for the ones out but not found, padlocks with arrival dates for days still to come, a progress bar, the coupon and voucher codes with their terms, the next riddle, the referral code with a "Copy invite link" button, and the coming sets. The nav shows "n/31" next to Account; the Home page strip shows "day n of 31".
- Guests can play: finds are kept in this browser (`localStorage`, friend keys only) and move to the account automatically at sign-in.

**Why it helps**

- *Shopper:* a reason to look around every page, a small win each time, a new friend to look for every day of October, codes that are theirs and saved, and a reason to come back when the next set arrives. Guests are not punished for not signing in yet.
- *Business:* daily visits through the Halloween season, return visits each new set, referrals that bring new accounts, and coupons tied to accounts so redemption can be measured. The voucher's terms (with purchase, in stock, while supplies last) keep it a sale, not a giveaway. The rules keep it a shop, not a game: one strip on the Home page, friends only where there is no text, no points or leaderboards, and the assistant answers hunt questions in a line or two and goes back to merch.

**Where to see it**

- Home page: the day's earliest unfound friend hides in the footer or the Halloween scene (add `?spot=footer` to pin the spot). Tap it, then follow the riddles.
- Account page, "My hidden friends": the 31-day tray, rewards, referral code, coming sets. Nav badge "n/31".
- Chat: "any clue where the friends are?" returns the next riddle with your count.
- Screenshots: `p9-hidden-friend-guest.jpg` (a guest finds Witch Totoro, next clue shown), `p9-coupon-three-finds.jpg` (third find, coupon issued), `p10-account-tray.jpg` (the 31-day tray with locked days).

---

## 2. Front end: Products you can actually narrow, with sizes on every card

**What we added**

- Filters that were missing from the page: sort (featured, price low to high, price high to low, name), max price, and "in stock only", next to the existing category and search. Every filter lives in the URL (`/products?category=hoodie&max_price=50&sort=price_asc`), so a filtered view can be shared or bookmarked, the back button works, and the assistant can hand a shopper a link to it. A "Clear filters" link and a status line ("27 products: hoodies, in stock, price: low to high") say what is applied.
- Size chips on every product card: XS to XXL, green for in stock, struck through (with a 👻 in Halloween mode) for sold out, read from the inventory table in one query (`ProductSummary.sizes_in_stock`). Screen readers get "M sold out" text, not colour.
- An empty result says so and offers "Show everything" or the assistant.

**Why it helps**

- *Shopper:* "a navy hoodie under $50 in my size" is two clicks and a glance, not a tour of item pages. No more opening five items to learn that medium is gone.
- *Business:* fewer abandoned browses, and fewer "do you have this in M?" questions that the page could have answered. The filters mirror what the assistant's search tool already accepts, so the page and the bot agree.

**Where to see it**

- Products page: the filter row and the chips on each card. Try `http://localhost:5173/products?category=hoodie&sort=price_asc&in_stock=true`.
- Screenshot: `p9-products-filters.jpg`.

---

## 3. Agent and back end: Restock requests (the assistant can file one; staff see what to order)

**What we added**

- A new agent tool, `request_restock(product_id, size)`, the agent's first and only write tool. The prompt offers it only after a sold-out answer and calls it only when the shopper says yes. The server, not the model, enforces the rules: the shopper must be signed in, the size must really be at zero in the database (a request for stock that exists is refused with the good news), one open request per shopper per product and size, ten open requests at most. Guests are invited to sign in.
- The same request from the item page: a "Request a restock" button on each sold-out row (`POST /me/restock-requests`), so shoppers who never open the chat get it too.
- The shopper's own list on the Account page ("My restock requests", with Cancel), so nothing is collected without being visible.
- A **Staff page** (`/staff`) for the emails listed in `ADMIN_EMAILS` (`backend/.env`): the queue grouped by product and size, most requested first, with who is waiting, a "Mark ordered" button and a CSV download (`GET /admin/restock-requests.csv`). The page says in plain words why you can see it ("this email is listed in ADMIN_EMAILS"); the Account page states each person's role (shopper or shop staff); the Staff link appears in the nav only for staff accounts; and the server answers 403 to everyone else, so a shopper who types the URL sees nothing.

**Why it helps**

- *Shopper:* a sold-out size becomes a waiting list instead of a lost sale, from the chat or the page, with a record they can see and withdraw.
- *Business:* a demand signal by exact product and size, with names and emails to contact, in a list or a spreadsheet. The staff's use of name and email is a documented purpose in the data dictionary and governance record.
- *Safety:* the write is typed, allow-listed to the signed-in shopper's own row, verified against the database before it happens, capped, and audited with ids only. Who is staff is decided by the server from an environment variable, never by the browser.

**Where to see it**

- Any item page with a sold-out size (for example `/products/baseball-left-chest-crewneck`): the Restock column.
- Chat on that page: "do you have this in XL?" then "yes please" files the request and links to the Account page.
- Account page: "My restock requests" and the role line. Signed in as the seeded test account (listed in `ADMIN_EMAILS` for the demo): the Staff link and page.
- Screenshots: `p9-restock-item-page.jpg`, `p10-staff.jpg`.

---

## 4. Agent and back end: Fewer dead ends and fewer clicks (alternatives, page stock in context, page links, clues)

**What we added**

- `find_alternatives(product_id, size)`: up to five items in the same category that have the wanted size in stock right now, nearest in price first, then by shared colours. The prompt pairs it with every sold-out answer, so "👻 Sold out in XS" is followed by "In XS right now: …" with cards.
- The product on screen now arrives in the agent's dynamic context with its stock by size, read from the database for that turn. A stock question about the item on screen is answered from that note instead of a tool round trip, which is one model call fewer (about 3 to 4 s on this laptop). Prices in the note are covered by the same post-reply price check as tool results.
- Page links: the agent's structured reply can carry a `go_to` link to a page of this site, with `navigate: true` only when the shopper asked to go. The harness validates every link before the browser sees it: only the site's own routes, product pages only for ids the tools returned this conversation, and Products query strings only if they pass the same `ProductQuery` model the API uses. Anything else is dropped and logged. The chat shows the link as a button and, when asked, opens the page.
- `hiding_clue()`: the riddle for the next unfound friend with the shopper's progress and how many friends are out so far, so the assistant can help with the hunt without inventing hiding spots.

**Why it helps**

- *Shopper:* every sold-out answer comes with a real next step; "take me to the hoodies under $50" lands on the filtered page in one go; questions about the item on screen come back faster.
- *Business:* alternatives keep the sale in the shop; page links cut the path from question to products; the saved round trip is cheaper per turn at the model.
- *Accuracy and safety:* the alternatives and the page note come from the database, the link validator keeps the model inside the site, and the prompt still forbids any price or stock the tools (or the page note) did not supply.

**Where to see it**

- Open `/products/baseball-left-chest-crewneck`, ask "do you have this in XS?": ghost, alternatives as cards, restock offer. Audit line for that turn: one tool call (`find_alternatives`), no stock lookup.
- Ask "take me to the hoodies under $50, cheapest first": the page moves to `/products?category=hoodie&max_price=50&sort=price_asc` and the chat shows "Opened: Hoodies under $50, cheapest first".
- Ask "any clue where the hidden friends are?": the riddle and your count.
- Screenshot: `p9-chat-alternatives.jpg`.

---

## Evidence

- Live run (2026-10-19, `gpt-5.6-luna` through Portkey), from `backend/output/audit.jsonl`:

  | Shopper said | Tools called | Page link | Seconds |
  |---|---|---|---|
  | do you have this in XS? | find_alternatives | none | 7.0 |
  | What about XL? If that is gone too, yes please ask them to reorder it in XL. | find_alternatives, request_restock | /account (offered) | 10.3 |
  | Any clue where the hidden friends are? | hiding_clue | none | 4.1 |
  | Take me to the hoodies under $50, cheapest first. | search_products | /products?category=hoodie&max_price=50&sort=price_asc (opened) | 5.6 |

- Database writes during the runs: `egg_finds` rows and one `coupons` row (10% at the third find) for the seeded account; two `restock_requests` rows (XS from the item page, XL from the chat), one later marked ordered from the staff view.
- Tests: `backend/tests/test_usability.py` covers sort and size chips, the public hunt programme (31 daily friends, seven characters, eight costumes, rotating home pages), daily unlocking (a locked friend is refused, the chase never points at one), finds and milestones (coupon at three, lift at ten, voucher at the full set, no second code), ten finds across seasons lifting the coupon once, referrals capped at three, account deletion cascade, the restock tool's refusals and dedupe, the shopper's own list and cancel, the staff queue and CSV with 403 for non-staff, alternatives, the page-link validator, the page-stock note, the clue tool, and season selection.
- Screenshots: `docs/screenshots/p9-products-filters.jpg`, `p9-hidden-friend-guest.jpg`, `p9-restock-item-page.jpg`, `p9-chat-alternatives.jpg`, `p9-coupon-three-finds.jpg`, `p10-account-tray.jpg`, `p10-staff.jpg`.
