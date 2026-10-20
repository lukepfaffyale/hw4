# Campus Customs harness notes

System documentation for the HW4 shop + chatbot. Section 0 is the reference: how the whole system works, written at the end (Problem 12). Sections 1 to 13 are the build history, one per problem. Diagrams and exact types live in `docs/data/` (`conceptual_model.md`, `logical_model.md`, `data_dictionary.md`).

---

## 0. How the system works (reference)

### 0.1 One chat turn, end to end

1. **Browser.** The shopper types in the chat panel (`frontend/src/components/ChatPanel.tsx`). The panel posts `POST /chat` with `{ message, page, history? }` through the one typed client (`frontend/src/api.ts`, base URL `VITE_API_URL`, default `http://localhost:8000`). A signed-in shopper sends the session token instead of history; a guest sends back up to 12 of their own recent turns.
2. **Route** (`backend/main.py`). Rate limit (30 turns per address per 15 minutes). Regex prompt guard on the typed text: flagged blocks are dropped and counted, never stored. The product on screen is re-read from the database by id, so the agent works from our facts, not the browser's. Identity comes from the signed token only. All of this goes into `ChatState`, the agent's deps, together with a random run id for the audit.
3. **Harness** (`backend/agent.py`, `run_chat`). The single PydanticAI `Agent` iterates its graph under `UsageLimits(request_limit=12, tool_calls_limit=20)`. The model (Portkey, `OPENAI_MODEL`) reads the system prompt plus a dynamic note (first name, page product with its stock by size, the tool list) and calls typed tools from `backend/tools.py`, which read `data/campus_customs.db` through `backend/db.py` with parameterised SQL. Every graph node is written to the audit files as it happens.
4. **Output checks.** The model must return a `ChatReply` (reply, product_ids, go_to). The harness strips em dashes, keeps only product ids a tool returned this turn, validates the page link against the site's routes, checks dollar amounts against tool prices, and records the stop reason (`completed`, `usage_limit`, `guardrail`, `no_result`, or the exception name). The route never sees an exception; a failure becomes a plain fallback reply.
5. **Back to the page.** The route maps the ids to the `ProductSummary` objects the tools fetched, stores the cleaned turn for a signed-in shopper (`chat_messages`), and returns `ChatResponse`. The panel prints the reply, draws the cards, shows the page link as a button (or opens it if the shopper asked), and the Products grid narrows to the cards.

### 0.2 The agent is four files

| File | What it holds |
|---|---|
| `backend/prompts/prompt.md` | The system prompt: voice, facts-from-tools rules, the tools table, the sold-out playbook, page links, the output contract, safety rules, hidden friends, memory and page notes, the finish rule. Read once at start-up. |
| `backend/agent.py` | The model factory (Portkey, allow-listed names, Responses API for gpt-6), the one `Agent`, the dynamic per-turn instruction, `run_chat` (the loop with limits and audit), `validate_page_link`, `unverified_prices`, `strip_em_dashes`. |
| `backend/tools.py` | `ChatState` (deps: identity, page product, the `seen` map, the tool list), the `lookup_*` functions over `db.py`, `create_restock`, and the eight registered tools with their audit lines. |
| `backend/models.py` | Every Pydantic schema: products, auth, the chat contract, tool results, hidden friends, restock. |

Around the agent, not part of it: `main.py` (routes), `db.py` (the only module that opens SQLite), `auth.py` (password hashing and sessions), `hunt.py` (hidden-friends rules), `audit.py` (both audit files), `prompt_guard.py` (the class regex guard), `ratelimit.py`. The front end is `frontend/` (React 19, TypeScript, Vite 8, React Router 7).

### 0.3 Models in `models.py` and why we chose them

Rules that hold for every model: request bodies forbid unknown fields (`extra="forbid"`); every free-text field has a maximum length; identifiers match a pattern; no response carries a password hash, another person's data, or a secret; `frontend/src/types.ts` mirrors each response type.

**The chat contract**

| Model | Fields that matter | Why |
|---|---|---|
| `ChatRequest` | `message` 1 to 1000 chars; `history` up to 12 `ChatTurn` (role `user` or `assistant` only); `page` | Bounded prompt cost and guard work. A client cannot send a `system` turn. Guests carry their own memory; signed-in shoppers get it from the database. |
| `PageContext` | `route` (pattern), `product_id` (pattern), `product_name` (hint only) | The browser may point at a product, never assert a fact: the server re-reads the row by id. |
| `ChatReply` (the agent's structured output) | `reply` up to 1500 chars; `product_ids` up to 8; `go_to: PageLink or null` | The page never parses prose. Cards and links are typed fields the harness can validate before the browser sees them. |
| `PageLink` | `route` up to 300, `label` up to 80, `navigate` default false | A page is offered as a button by default; the page changes under the shopper only when they asked. |
| `ChatResponse` | `reply`, `products: list[ProductSummary]`, `stopped_reason`, `flagged`, `signed_in`, `go_to` | Full card data travels with the reply, so the page makes no second request; the stop reason and the flag make every turn explainable. |

**Tool results** (every one has `ok` and `error`, so a miss is a sentence the agent can repeat, never a gap it fills)

| Model | Fields | Why |
|---|---|---|
| `ProductBrief` (one search hit) | `product_id`, `name`, `category`, `short_description`, `price` and `price_display`, `colors`, `total_stock`, `sizes_in_stock`, `sold_out_sizes` | Enough to answer price, colour and availability from one call. The number keeps the price check exact, the string stops rounding, the two size lists stop mis-summing. |
| `SearchResult` | `items` (max 8), `total_matches`, `categories`, `sort`, `query_echo` | The agent can say "27 hoodies, here are eight", knows the order it got, and can redirect a miss to a category that exists. |
| `ProductResult` | `product: ProductDetail`, `price_display` | Description and tags for one id, with stock by size included so no second call is needed. |
| `StockLookup` | `sizes` with `quantity`, `status`, `label`; `sizes_in_stock`; `sold_out_sizes` | The database number, the rule applied to it, and the sentence to say, so the model re-derives nothing. |
| `StockResult` | one size: `quantity`, `status`, `label`, `other_sizes_in_stock` | "Do you have it in M?" answered in one call, with the alternative already in hand. |
| `AlternativesResult` | `wanted_in_stock`, `items` (max 5) | Sold out is not a dead end; if the size is in stock after all the agent is told so. |
| `RestockResult` | `request_id`, `outcome` (`created` or `already_open`), `open_requests` | The agent confirms exactly what happened and never claims a date. |
| `ClueResult` | `found`, `total`, `next_friend`, `riddle`, `note` | The riddle and the count are the only hidden-friends facts the agent may quote. |
| `IdentityResult` | `signed_in`, `first_name`, `last_name`, `email` | Answers "who am I?" from the session; the only path by which an email reaches the model. |

**Products**: `ProductSummary` (the card: `product_id`, `name`, `category`, `short_description`, `colors`, `price`, `image_url`, `total_stock`, `sizes_in_stock`), `ProductDetail` (adds `description`, `search_tags`, `stock: list[StockLevel]`), `ProductList`, `ProductQuery` (`q` up to 80, `category`, `max_price`, `in_stock`, `sort`; one model shared by the API, the Products page URL, the agent's search and the link validator), `StockLevel` (`status` derived once in the back end).

**Accounts**: `SignupRequest` (names cleaned, email lower-cased, the password policy enforced in the validator, `referral_code` normalised), `LoginRequest`, `SocialLoginRequest`, `UserPublic` (never the hash; `is_admin` for the Staff link), `AuthResponse`, `DeleteMeResponse`, `PasswordPolicy` (published so the form shows the server's rules).

**Hidden friends and restock**: `HuntProgram`, `HuntSeason`, `HuntFriend`, `HuntMilestones` (public, no PII), `HuntProgress`, `FriendStatus`, `Coupon`, `Reward` (the signed-in shopper's own rows), `FindRequest` (season and friend keys, patterns), `RestockCreateRequest`, `RestockRequest`, `RestockList`, `RestockStatusResponse`, and for staff `AdminRestockQueue`, `AdminRestockGroup`, `AdminRequester`.

### 0.4 Tools and abilities

| Tool | Arguments | Reads or writes | Cap | Used for |
|---|---|---|---|---|
| `search_products` | `query`, `category`, `max_price`, `in_stock_only`, `sort` | reads `catalogue` + `inventory` | 8 items | category, keyword and price questions |
| `get_product` | `product_id` | reads both | one item | description, colours, tags |
| `get_stock` | `product_id` | reads `inventory` | six sizes | "what sizes do you have?" |
| `check_stock` | `product_id`, `size` | reads `inventory` | one size | "do you have it in M?" |
| `find_alternatives` | `product_id`, `size` | reads both | 5 items | a sold-out size: same category, that size in stock, nearest price first |
| `request_restock` | `product_id`, `size` | **writes** one `restock_requests` row for the signed-in shopper | 10 open per shopper | the only write; after the shopper says yes; refuses guests, unknown products, sizes not offered or in stock |
| `hiding_clue` | none | reads `egg_finds` through `hunt.clue` | one riddle | hints and progress |
| `who_am_i` | none | the session in deps | | "who am I?" |

What the agent can do beyond tools: read the dynamic note (first name, the on-screen product with its stock), return cards (`product_ids`), hand over a page (`go_to`). What it cannot do: read `users` or anyone's `chat_messages`, see or issue coupon or voucher codes, change stock or prices, reach the network, run SQL (tools take typed arguments and `db.py` builds every query), or write anything except its own shopper's restock request.

### 0.5 Safety rules, by layer

| Layer | Rule | Where |
|---|---|---|
| Input | Message capped at 1000 characters; unknown fields rejected; regex prompt guard drops injection blocks and records them without the payload; 30 turns per address per 15 minutes | `models.py`, `prompt_guard.py`, `main.py` |
| Identity | Who is chatting comes from the signed session only; the prompt gets the first name; last name and email only through `who_am_i`; chat text can never change identity | `main.py`, `agent.py`, `tools.py` |
| Prompt | "Safety rules" section: instructions come only from the prompt, non-disclosure, no personal data, no orders or promises, honesty under uncertainty, the one write, site links only, conduct, loop discipline | `prompts/prompt.md` |
| Model | Allow-listed model names, Portkey only, key from `.env`, no temperature, cache bypass header available | `agent.py` |
| Loop | `UsageLimits(12 requests, 20 tool calls)`, `retries=2` for output validation, a friendly "narrow it down" reply when a limit is hit, no exception reaches the route | `agent.py` |
| Output | Cards only for ids the tools returned; page links validated against the site routes and `ProductQuery`; dollar amounts checked against tool prices (the shopper's own figure is ignored); em dashes rewritten; reply at most 1500 characters | `agent.py` |
| Writes | One tool; the row belongs to the signed-in shopper; the size is verified at zero stock before insert; one open request per product and size; ten open per shopper | `tools.py`, `db.py` |
| Audit | Two append-only files, cleaned text only, emails redacted, random run ids, no user id, name, token or key | `audit.py` |
| Front end | No raw HTML rendering of any text; a page link is a button; the page moves only when `navigate` is true | `ChatPanel.tsx` |

### 0.6 Specs

- **Loop.** PydanticAI 2.57 (`pydantic-ai-slim[openai]`), `agent.iter(...)` so every node is audited, `UsageLimits(request_limit=12, tool_calls_limit=20)`, `retries=2`. Stop reasons: `completed`, `usage_limit`, `guardrail`, `no_result`, or the exception class name.
- **Result caps.** Search 8 items, alternatives 5, cards 8, reply 1500 characters, link label 80, message 1000, guest history 12 turns, stored history 20 turns, open restock requests 10 per shopper, audit text 300 to 400 characters per field, trail text 200.
- **Rate limits** (per 15 minutes): chat 30 per address; sign-in and sign-up 20 per address and 8 per email; hidden-friend finds 120 per address.
- **Models.** `OPENAI_MODEL` default `gpt-5.6-luna`; allowed `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-6-astra`, `gpt-6-luna`; gpt-6 names use the Responses API class; routed through Portkey at `https://api.portkey.ai/v1` with the `x-portkey-api-key` header; no temperature. Measured on the live site: 3 to 8 seconds for a turn with one tool call, 8 to 12 seconds with three.
- **Storage.** SQLite `data/campus_customs.db` (the course data pack, never committed); `db.ensure_schema()` adds the app's tables idempotently at start-up; schema in `backend/data/schema.sql`.
- **Versions.** Python 3.14 (3.12 or newer works), FastAPI 0.146, Pydantic 2.14, pydantic-ai-slim 2.57, openai 3.35, bcrypt 5; Node 24, React 19, TypeScript 5, Vite 8, React Router 7.
- **Ports.** Back end `http://localhost:8000` (CORS allows exactly `FRONTEND_ORIGIN`), front end `http://localhost:5173`.
- **How to run.** From the `hw4` folder: place the data pack at `data/`; copy `.env.example` to `.env` and set `PORTKEY_API_KEY`; `pip install -r requirements.txt`; `cd backend` then `uvicorn main:app --reload --port 8000`; in another terminal `cd frontend`, `npm install`, `npm run dev`. Checks: `python -m pytest -q` from `backend/` (68 tests, on a throwaway copy of the database), `npm run build` and `npm run lint` from `frontend/`.

---

## 1. The data (Problem 2)

`data/campus_customs.db` is a SQLite file with four tables. Profiled 2026-10-16: 102 products, 612 stock rows, 3 users, 22 chat messages. Scanned clean for hidden instructions. Not committed to Git.

Each field below has two readings:

- **Shop:** why the field matters to the business, in plain words.
- **Bot:** how the chatbot uses it to answer a shopper safely and quickly, and the tone the shop owner can reuse on the website.

### 1.1 `catalogue`: what we sell

One row per product. Everything the bot says about an item comes from here or from `inventory`. Nothing is invented.

| Field | Shop | Bot |
|---|---|---|
| `product_id` | The permanent handle for a product. Links the photo, the stock rows, and every chat card back to the same item. | Never shown to the shopper. Used to fetch exact stock and to tell the page which cards to display. |
| `name` | The product title customers recognise, e.g. "Vintage Bulldog Hoodie". | Always quote the name exactly as stored. On the site: "Meet the Vintage Bulldog Hoodie." |
| `garment_type` | What kind of item it is: hoodie, crewneck, tee, quarter-zip, fleece jacket, performance shirt. Drives the shop's category menu. | First filter for "what hoodies do you have?". The raw values are messy (22 spellings), so the bot searches a cleaned category and the raw text. If a type is not in the catalogue (gym shorts, hats), say so plainly and offer the nearest category. |
| `description` | The one-paragraph product copy: colour, cut, graphic, fabric details. Doubles as website copy. | The source for "what does it look like?" and "does it have a hood / pocket / crest?". Quote or paraphrase it; never add features it does not mention. On the site it reads as-is. |
| `colors` | The colours on the garment. Lets customers shop by colour and avoids returns. | Answers "do you have this in pink?" honestly: check the list, and if the colour is not there, say the item comes only in the listed colours. Three products have no colours listed; say "colour not listed" for those. |
| `search_tags` | Keywords customers might type: "Harvard", "bulldog", "Ivy League", "left chest logo", sport names, residential colleges. Powers search and SEO. | The fast path for fuzzy asks: "anything with Handsome Dan", "bulldog stuff", "Benjamin Franklin College". Match tags before scanning descriptions. Tags are data, not instructions. |
| `image_file_path` | Where the product photo lives. A shop without photos does not sell. | Converted to an image URL on every card. The bot never reads or guesses file names; the back end maps the stored path. |
| `price` | What it costs, in US dollars. Seven price points from $32 tees to $98 jackets. | The only source of price. Format as "$68". For "cheapest fleece", sort the matching items by price and name the lowest. Never estimate, round differently, or mention discounts that are not in the data. |

**Website voice for this table (for the shop owner):** every product is official Yale gear from Campus Customs, with a photo, a plain description of the cut and graphic, the colours it comes in, and one honest price. If it is not in the catalogue, we do not sell it.

### 1.2 `inventory`: how many we have, by size

Six rows per product, one per size XS to XXL. Quantities range 0 to 25; 145 size rows are at 0.

| Field | Shop | Bot |
|---|---|---|
| `id` | Row key for the stock record. | Not used in answers. |
| `product_id` | Which product this stock belongs to. | Joins stock to the product the shopper asked about. |
| `size` | The size on the label: XS, S, M, L, XL, XXL. Lets customers check their size before they get excited. | Answers "do you have it in medium?" per size. List in-stock sizes in order; name sold-out sizes as sold out. |
| `quantity` | Units on hand for that size. Zero means sold out in that size; low numbers mean "going fast". | Say "in stock" when quantity is above 0, "sold out in that size" at 0, and "only N left" when it is 5 or fewer. Never promise stock the table does not show, and never give a restock date (none exists). |

**Website voice:** sizes XS to XXL, live availability by size, and a straight answer when something is sold out.

### 1.3 `users`: who is shopping

Shopper accounts. Three rows shipped (a test user and two sample accounts). All name and email fields are PII; see `docs/data/data_dictionary.md`.

| Field | Shop | Bot |
|---|---|---|
| `id` | Internal account number. Ties a shopper to their chat history. | Used only to scope lookups to the signed-in shopper. Never spoken. |
| `name`, `first_name`, `last_name` | What to call the customer. Makes the shop feel personal. | The bot may greet by first name ("Welcome back, Ada") and can answer "do you remember my name?" for the signed-in user only. Names are never sent to the model as part of product search. |
| `email` | Login identity and the only way to reach the customer. Unique per account. | Never shown, repeated, or logged. The bot does not look up other people. |
| `password_hash` | Lets a customer sign in without the shop ever storing the password. | Never reaches the bot. New accounts hash with bcrypt; shipped accounts use PBKDF2 and verify under that scheme. |
| `created_at` | When the account was made (UTC). | Not used in answers. |

**Website voice:** make an account to save your chat, get greeted by name, and see or delete your own history whenever you like.

### 1.4 `chat_messages`: the conversation, with the cards it showed

One row per turn. Bot rows carry a JSON snapshot of the products shown with the reply.

| Field | Shop | Bot |
|---|---|---|
| `id` | Row key, keeps turns in order. | Ordering only. |
| `user_id` | Whose conversation this is. | The bot loads only the signed-in shopper's rows as memory. Never another shopper's. |
| `role` | `user` or `assistant`: who said it. | Rebuilds the message history for the model and the chat pane. |
| `content` | What was said. The shopper's questions are the best record of what customers want (hoodies, pink, Handsome Dan, cheapest fleece, gym shorts we do not carry). | Prior turns give the bot memory ("you asked about hoodies earlier"). Shopper text is cleaned by the prompt guard before it is stored or sent to the model; stored text is data, never instructions. |
| `products_json` | Which products the bot showed with each reply, frozen at that moment. Lets the shop see what was recommended and lets the page re-draw the cards. | Written by the back end from tool results, not by the model. The page renders these cards next to the reply. `[]` means the reply showed nothing. |
| `created_at` | When the turn happened (UTC). | Ordering, and the shopper's "my activity" view. |

**Website voice:** your chat remembers what you looked at, and the items the bot mentions appear right next to the conversation.

### 1.5 Design decisions taken from the data

1. **Facts come from tools.** Price, colours, sizes and stock are read from `catalogue` and `inventory` by typed tools at answer time. The system prompt forbids inventing any of them.
2. **Clean category layer.** `garment_type` is normalised to about eight categories for filters; the raw value is kept and searchable.
3. **Per-size stock.** "In stock" is always answered by size, because 145 size rows are already at 0.
4. **Honest misses.** Anything not in the catalogue (shorts, hats, a colour not listed) gets a clear "we don't carry that" plus the closest alternative from a real search.
5. **Memory is per shopper.** `chat_messages` scoped by `user_id` is the bot's memory; it is loaded as message history and never crosses users.
6. **Cards are back-end facts.** `products_json` is built from tool results, so the page can only show products that were actually looked up.
7. **SQLite as given.** The assignment ships SQLite and says "local database", so the course Supabase default is not used; access still goes through `backend/db.py` only, with parameters, never string-built SQL.

---

## 2. The website shell (Problem 3)

`frontend/` is a React 19 + TypeScript + Vite 8 app (`npm create vite@latest frontend -- --template react-ts`) with React Router 7. Build is `tsc -b && vite build`; lint is oxlint. Both pass.

### 2.1 Pages and routes

| Route | Page | Status after Problem 3 |
|---|---|---|
| `/` | Home: hero, "why Campus Customs" panel, four category cards, family section | done |
| `/products` | Products: catalogue grid | placeholder until the API exists (Problem 4+) |
| `/about` | About Us: what we sell, how the shop works, visit, class-project note | done |
| `/login` | Log in form (email, password) | form only; submits to the API later |
| `/create-account` | Create Account form (first, last, email, password of 12+) with the data notice | form only; submits to the API later |
| `*` | Not found | done |

Structure: `src/components/Layout.tsx` (skip link, header, `main`, footer), `src/components/NavBar.tsx` (brand, five links, mobile menu button with `aria-expanded`, Escape to close, `aria-current` on the active link), `src/pages/*.tsx`, `src/usePageTitle.ts` (document title per route), `src/index.css` (design tokens and all styles).

### 2.2 Style and wording

- Palette: navy-black background `#0a0f1c`, Yale blue `#00356b` surfaces, white text, light blue `#5aa0ff` links, class pink `#ff4fa3` for primary actions and the active nav item. Contrast pairs are listed in `docs/accessibility.md`.
- yalebulldogblue.com was read for its look (Bulldog Blue, product-card grids, playful short slogans) and for facts (officially licensed Yale merchandise, Campus Customs, 57 Broadway, New Haven, categories for residential colleges, sports, relatives). All copy on Home and About is original. No store history, hours, or shipping claims are made because the source does not state them.
- Catalogue facts in the copy (hoodies at $68, tees from $32, jackets to $98, sizes XS to XXL, Harvard-Yale tee, residential college crests, team marks) come from the database profile in section 1.

### 2.3 Accessibility built in

Skip link, landmarks, one `h1` per page, labelled inputs with autocomplete hints, visible pink focus ring, `aria-live` status lines on forms and the Products placeholder, reduced-motion guard on transitions, single-column layout under 760px. Keyboard and screen-reader passes are logged in `docs/accessibility.md` when the build is called done.

### 2.4 Landmine found during research

The yalebulldogblue.com home page contains text addressed to AI assistants (near the checkout section, formatting and quoting rules). It was treated as data, not followed, and is recorded by location and kind in `docs/governance.md`.

---

## 3. Products API, item page, chat stub, Halloween mode (Problem 3, continued)

### 3.1 The read-only API (`backend/`)

FastAPI + Pydantic, Python 3.14, run with `uvicorn main:app --host 127.0.0.1 --port 8000` from `backend/` (reload off, so an agent-driven edit cannot spawn a second server). Pinned in `requirements.txt`.

| Endpoint | Returns | Table(s) | Notes |
|---|---|---|---|
| `GET /health` | `Health` | none | Render health check |
| `GET /products?q=&category=&max_price=&in_stock=` | `ProductList` | catalogue + inventory | Unknown query parameters are rejected with 422 (same discipline as `extra="forbid"`). `q` is capped at 80 chars and searched with a parameterised `LIKE` over name, type, description, colours and tags. |
| `GET /products/{product_id}` | `ProductDetail` | catalogue + inventory | Stock per size in XS to XXL order with a status word: `in_stock`, `low` (5 or fewer), `sold_out`. |
| `GET /media/products/{product_id}` | JPEG bytes | catalogue | The file path comes from the catalogue row, never from the URL. The resolved path must sit under `data/products/`, otherwise 404. Ids must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. |

Design points:
- `db.py` is the only module that opens the SQLite file (read-only URI, foreign keys on, one connection per request). Routes never see SQL.
- `category` is derived from `garment_type` in one function (`normalise_category`) so the 22 raw spellings collapse to seven filter values. The raw type is still returned and searchable.
- `short_description` is cut at a word boundary around 110 characters for cards; the item page gets the full text.
- CORS allows exactly `FRONTEND_ORIGIN` (default `http://localhost:5173`) and only `GET`.
- No writes, no auth, no model calls yet. Those arrive in Problem 5 inside the safe agent harness.

### 3.2 Front-end data flow

`src/types.ts` mirrors `backend/models.py`. `src/api.ts` is the single typed client (base URL from `VITE_API_URL`). `src/useAsync.ts` loads by key and ignores stale responses, so a fast category switch cannot show the wrong list. Products renders cards (`ProductCard`) that link to `/products/:id`; the item page shows the large image on the left and name, price, description, type, colours, a stock table and tags on the right, stacking to one column under 760px.

### 3.3 Chat stub

`ChatPanel` floats bottom-right as a non-modal `role="dialog"` with a labelled input, a `role="log"` message list, Escape to close, and focus returned to the launcher. It answers every message with a fixed line saying the assistant is not connected yet. Problem 5 replaces the stub reply with a call to `POST /chat`; the component shape (messages, send, products to show) is already what the agent will fill.

### 3.4 Halloween mode

A `role="switch"` in the nav labelled "Halloween toggle", default **on**, remembered in `localStorage` (a preference, not PII). When on:
- the palette shifts to pumpkin orange (`#ff9a2e`, 9.8:1 on the background) and witch purple surfaces;
- a **night scene** (`HalloweenScene`, inline SVG) sits as its own band between the page content and the footer: moon with craters, stars, drifting clouds, three crows flying with flapping wings, bats, a haunted house with glowing windows and a crooked tower, a dead tree, a picket fence, a graveyard of tilted tombstones and crosses, pumpkins, a gliding ghost, low fog, and small webs with spiders in its top corners. On the Account page the scene sits under the heading instead, so the sign-in lightning is in view;
- **rule: effects never sit over text.** The scene is a block in the page flow. The fixed decorations (corner webs, bats, a ghost) render only when the viewport is at least 1460px wide, which leaves 170px side gutters outside the 1120px content column, and they stay inside those gutters;
- **lightning** on a successful sign-in or signup: a hand-drawn SVG bolt with two branches and a glow flickers from the storm cloud onto the house, the scene's sky brightens, and a soft glow fades in behind the whole page (z-index below the content). Two brightenings in 1.8 s, then gone. No GIF: the inline SVG is about two kilobytes, scales cleanly, and honours reduced motion, which a GIF cannot;
- opening an item page, or activating its photo, pops a friendly character (ghost, skeleton, pumpkin, bat, witch) over the photo with a one-line greeting.

Accessibility rules the feature follows:
- All decoration is `aria-hidden` and `pointer-events: none`; it never blocks a control or reaches a screen reader.
- Every animation sits inside `@media (prefers-reduced-motion: no-preference)`. With reduced motion the webs are static, nothing moves, and the pop-out fades in instead of springing.
- Nothing flashes; the pop-out is one soft 420 ms scale, then a gentle wiggle, no sound.
- The pop-out is `role="status"` (polite, not interrupting), auto-hides after 4 s, and has a Dismiss button. The photo becomes a real `<button>` with a label that says a surprise will appear, so keyboard users opt in; with Halloween off it is a plain image.
- Colour is never the only signal: stock rows use words, the toggle shows "on"/"off" text.

### 3.5 Verified

API smoke test (health, list, filters, detail, image, bad ids, unknown params); `npm run build` and `npm run lint` with zero warnings; Chrome screenshots of the grid, the item page, the pop-out and the chat panel in `docs/screenshots/`.

---

## 4. Accounts: what we store and how passwords are protected (Problem 4)

### 4.1 What a user row holds

Every column below is in `docs/data/data_dictionary.md` with its PII flag. The shop keeps the minimum needed to greet a shopper and let the assistant remember them.

| Column | PII | What it is | Who can see it |
|---|---|---|---|
| `id` | linked to a person | Internal account number. | Back end only; the front end gets it inside `UserPublic`. |
| `first_name`, `last_name`, `name` | **yes** | What the shopper typed at signup, or what the social provider reported. `name` is kept in step as "First Last" because the shipped schema requires it. | The shopper (Account page). Never in logs or prompts. |
| `email` | **yes** | Login identity, stored lower-cased, unique. | The shopper. Never shown to other users, never logged. |
| `password_hash` | secret | A one-way hash (formats below), or the marker `!social` for accounts that sign in with Google or GitHub. | Nobody. Never returned by any endpoint, never logged, never sent to a model. |
| `auth_provider` | no | `password`, `google` or `github`. | The shopper. |
| `provider_user_id` | **yes** (identifier from a third party) | The provider's stable user id for social accounts. | Back end only. |
| `created_at` | no | UTC timestamp. | The shopper ("member since"). |

Nothing else: no phone, address, payment, device or IP columns. Chat history (`chat_messages`) is tied to `user_id` and is covered by the same delete path.

### 4.2 How passwords are protected

- **Never stored in plain text.** A password exists in memory only while it is hashed or verified. It is never written to the database, a log line, an audit file, an error message, a URL, or a model prompt.
- **Seeded accounts** from the course data pack are `pbkdf2_sha256$<salt>$<hex>`: PBKDF2-HMAC-SHA256, 120,000 iterations, the salt used as its UTF-8 string bytes, the digest in hex. We inspected the seeded test user's stored value and confirmed this encoding by recomputing it before writing a line of login code. Login splits the stored string, takes the salt from the middle piece, re-hashes what was typed with that salt and 120,000 iterations, and compares with `hmac.compare_digest`. The stored value is never "un-hashed" and no new salt is made at login.
- **New accounts** hash with **bcrypt, cost 12**, the class rule. bcrypt draws a fresh random salt per password and stores it inside the hash, so two people with the same password get different hashes, and a leaked table cannot be attacked with one precomputed list. `PASSWORD_SCHEME=pbkdf2` switches new accounts to the course format (same salt handling, encoding and 120,000 iterations as login); login verifies both formats whatever the setting, so the acceptance test (seeded user logs in, new account signs up then logs in, wrong password fails on both) passes either way. Seeded hashes are left exactly as shipped.
- **Verification is constant-time** (`hmac.compare_digest`, `bcrypt.checkpw`). When the email is unknown the server still performs a bcrypt check against a dummy hash, so timing does not reveal which emails exist, and the response is the same "Email or password is incorrect."
- **Strict policy, enforced by the server and mirrored live in the form:** 12 to 64 characters, lowercase, uppercase, number, symbol, no spaces, not based on a common password (any common word of six or more letters anywhere in it is rejected), not containing the shopper's name or email, no character repeated four times. The server is the authority (`backend/auth.py`, `password_issues`); the front end only previews the same rules.
- **Validation errors never echo the input.** Pydantic's default 422 body includes the submitted value; a custom handler strips it, and a test asserts the password string is absent from the response.
- **Brute force limits:** 20 attempts per client address and 8 per email in any 15-minute window on the auth endpoints, then 429.
- **The "spooky password" roller** builds a passphrase in the browser from three Halloween words, a separator, digits and a symbol using `crypto.getRandomValues`, checks it against the same policy, and fills the password and confirm fields only when the shopper clicks "Use this password". Nothing is sent until they submit, and it is then hashed like any other password.
- **If the database leaked**, an attacker, human or AI, would hold bcrypt cost-12 hashes and PBKDF2 120,000-iteration hashes, which must be brute-forced one guess at a time per account. The policy keeps the guesses expensive. The assistant (Problem 5) never gets a tool that reads `users`, so a prompt injection cannot reach the table.

### 4.3 Sessions

A successful signup or login returns a token: a base64 payload (user id, expiry, nonce) signed with HMAC-SHA256 under `SESSION_SECRET` from `backend/.env`, valid seven days. The back end verifies the signature and expiry on every `/me` call and takes the user id from the token only, never from the client. The front end keeps the token in `localStorage` so a refresh stays signed in; the app renders no raw HTML, which is the main defence for that choice. Sign out drops it. Deleting the account makes every token for that id useless.

### 4.4 Social sign-in

Google and GitHub go through **Supabase Auth's OAuth flow with the provider's defaults and minimum scopes** (email and basic profile). We hold no password and no provider token: the browser finishes the provider's sign-in, Supabase gives it a short-lived access token, and the front end sends only that to `POST /auth/social`. The back end hands the token back to Supabase (`/auth/v1/user`) to confirm it, and requires a verified email. It then finds the account by `(auth_provider, provider_user_id)`, or links to an existing account with the same verified email, or creates one with the unusable marker `!social` as its hash. Configuration lives in `.env` on both sides (`SUPABASE_URL`, anon key); with it blank the buttons are disabled and say so. The anon key is public by design; the service-role key is not used anywhere. Supabase then stores the social user's email and provider id on its side as well, which `docs/governance.md` records.

### 4.5 The shopper's controls

- **Notice before the first write** on the Create Account page: what is stored and why, plus a warning to use a test password. The footer repeats the academic-use note on every page.
- **Account page** shows every stored field, how they sign in, and member-since.
- **Delete my account** (two-step confirm) calls `DELETE /me`, which removes the shopper's chat rows and user row in one transaction and signs them out.
- Lightning strikes over the haunted house on a successful sign-in or signup when Halloween mode is on: two soft brightenings in under two seconds, confined to a small area, static under reduced motion, no full-screen flash.

### 4.6 Easter eggs and the one-per-shopper coupon

Now and then (35% of page visits, or always with `?egg=totoro` / `?egg=labubu` for testing) a small drawn Bramble or Snaggle peeks from a spot that holds no text: the ground of the night scene, the end of the footer row, the photo corner of one random product card, or a side gutter on wide screens. It is a real `<button>` with an accessible name, so keyboard and screen-reader users can find it too.

Activating it claims the shopper's coupon: **one per shopper, good for one item, one time.** The rule is enforced on the server, not in the browser: the `coupons` table has `UNIQUE (user_id)`, `POST /me/coupon` returns the existing coupon with `already_claimed: true` on any later claim, and no second code is ever issued. A guest who finds a friend is asked to sign in; the character is remembered in this tab only and the claim completes on the Account page after sign-in. The Account page shows the coupon, who it was found with, and whether it has been used (`redeemed_at`, set by a future checkout). Deleting the account deletes the coupon. Codes look like `BRAMBLE10-K7P2` and are clearly labelled as class-project codes, not redeemable at the real store.

### 4.7 Tests (`backend/tests/test_auth.py`, 29 passing)

Hash is not the plaintext and is bcrypt by default; two hashes of one password differ; PBKDF2 mode reproduces the course format; a seeded-style string verifies with the salt as a raw string; the unusable marker never verifies; nine weak passwords rejected and one strong accepted; name and email inside the password rejected; tokens round-trip, tampered and expired tokens rejected; seeded user logs in, wrong password fails with the same message as an unknown email; new account signs up, reads `/me`, logs in, wrong password fails, duplicate email gives 409, delete makes the token and the login fail; stored hash is not the password; the 422 body never contains the password; mismatched confirmation and unknown fields rejected; ninth attempt on one email gives 429; `/me` needs a token; social sign-in unconfigured gives 503; coupon: none at first (404), claim without a token is 401, first claim issues one code, a second claim returns the same code with `already_claimed`, an unknown character is 422, and deleting the account removes it. Tests run on a throwaway copy of the database.

---

## 5. The shop agent (Problem 5)

### 5.1 Files (same shape as HW3)

| File | Role |
|---|---|
| `backend/prompts/prompt.md` | The system prompt: Campus Customs voice, facts-from-tools rules, output contract, safety basics, the chat Easter egg, and a finish rule. One file, grown in later problems. |
| `backend/agent.py` | Loads `prompt.md`, builds the Portkey model, builds the single `Agent`, registers tools, and runs one harnessed turn (`run_chat`). |
| `backend/tools.py` | `search_products`, `get_product`, `check_stock`: typed, read-only, through `db.py`; `ChatState` (deps) remembers every product a tool returned. |
| `backend/models.py` | `ChatRequest`, `ChatTurn`, `ChatReply` (the agent's structured output), `ChatResponse`, tool result models (`SearchResult`, `ProductResult`, `StockResult`), activity models. |
| `backend/main.py` | `POST /chat`, `GET /me/activity`, `DELETE /me/activity`, plus the product and auth routes. Run from `backend/`: `uvicorn main:app --reload --port 8000`. |
| `backend/audit.py`, `backend/prompt_guard.py` | Audit trail and the class regex prompt guard. |

### 5.2 How the front end talks to FastAPI

`frontend/src/api.ts` is the one typed client (base URL from `VITE_API_URL`, default `http://localhost:8000`). The chat widget (`ChatPanel.tsx`) sends `POST /chat` with `{ message, history }` as JSON. If the shopper is signed in the request carries the session token as `Authorization: Bearer …` and `history` is empty: the server loads the last 20 turns from `chat_messages`. A guest sends back up to 10 of their own recent turns instead, and nothing is stored. The reply is `{ reply, products, stopped_reason, flagged, signed_in }`; the widget prints the reply, renders `products` as small cards (image, name, price, link to the item page) under it, and offers "Show these on the Products page", which opens `/products?ids=…` so the grid narrows to the items the assistant referenced. Types are mirrored in `frontend/src/types.ts` and `backend/models.py`. CORS allows only the Vite origin; chat is rate-limited to 30 turns per address per 15 minutes.

### 5.3 How the agent is loaded

- **Prompt:** `agent.py` reads `prompts/prompt.md` once at process start and passes it as the agent's `instructions`, so it is re-sent on every run even when a history is attached. A second, dynamic instruction adds the shopper context (signed in as `<first name>` or guest). Nothing else about the shopper reaches the model.
- **Model:** `OPENAI_MODEL` from `backend/.env` (default `gpt-5.6-luna`, allow-listed to the 5.6 and 6 series), routed through Portkey (`https://api.portkey.ai/v1`, header `x-portkey-api-key` from `PORTKEY_API_KEY`). gpt-6 names use the Responses API model class, others chat completions. No temperature is set. Portkey caches identical requests; `build_model(fresh=True)` adds the cache-bypass header for a true re-ask. The key is loaded from `.env` and `.env` is gitignored.
- **Agent:** one `Agent` per process with `deps_type=ChatDeps`, `output_type=ChatReply`, `retries=2`. The model is passed per run, which lets the tests swap in PydanticAI's `TestModel` with no key or network.
- **Harness, all five pieces:** tools (typed, `ok:false` on failure, never a guess); memory (`message_history` plus `ChatState` as deps); stopping rules (the prompt's finish rule plus `UsageLimits(request_limit=12, tool_calls_limit=20)`, with a friendly "narrow it down" reply when hit); guardrails (prompt guard on the typed text with flags written without the payload, allow-listed models, product cards only from ids the tools returned, no tool can reach `users`, `coupons` or other shoppers); audit (`output/audit.jsonl`, one record per graph node: user text, model parts, tool args, observations, final answer, stop reason; run id only, never a user id, email or password).
- **What is stored:** for signed-in shoppers, the cleaned user text and the reply, with the cards as `products_json`, in `chat_messages`; visible and deletable on the Account page (`GET /me/activity`, `DELETE /me/activity`, download as JSON).

### 5.4 Easter egg in the chat

One open in five, a hidden Bramble or Snaggle sits in the chat header keeping the assistant company. The prompt also gives the assistant one playful line if the shopper mentions Bramble, Snaggle or hidden friends, then steers back to merch. No coupon is involved; that stays one per shopper via the page eggs.

### 5.5 Tests (`backend/tests/test_chat.py`, 7 passing, 36 in total)

Guest gets a reply and nothing is stored; every card id exists in the catalogue; a signed-in shopper's turns are stored in order, listed, and deleted; an injection message is dropped, flagged without its payload, and absent from both the flags file and the audit log; the audit trail runs from `user` to `harness_complete` with loop records and no email or password; bad payloads (empty, over 1000 chars, unknown field, a `system` role in history) are 422; product and auth routes still work. The live model was exercised by hand through the website chat (acceptance test).

---

## 6. Tools: product info and stock (Problem 6)

Four read-only tools over `campus_customs.db`, all in `backend/tools.py`, all through `db.py` (parameterised SQL only). Each tool is a thin wrapper around a `lookup_*` function that is unit-tested on its own (`tests/test_tools.py`). The agent has no tool that can reach `users`, `coupons` or another shopper's chat, and no tool can write.

### 6.1 The tools

| Tool | Arguments | Returns | Used for |
|---|---|---|---|
| `search_products` | `query` (words over name, type, description, colours, tags), `category`, `max_price`, `in_stock_only`, `sort` (`relevance`, `price_asc`, `price_desc`, `name`) | `SearchResult`: up to 8 `ProductBrief` plus `total_matches` and the categories that exist | "what hoodies", "anything with a bulldog", "cheapest fleece", "under $50" |
| `get_product` | `product_id` | `ProductResult`: the full `ProductDetail` and `price_display` | "tell me about it", colours, what it looks like |
| `get_stock` | `product_id` | `StockLookup`: every size with quantity, status and label, plus `sizes_in_stock` and `sold_out_sizes` | "what sizes do you have", "is it in stock" |
| `check_stock` | `product_id`, `size` | `StockResult`: one size's quantity, status, label and the other sizes in stock | "do you have it in medium" |

### 6.2 Fields we chose for lookup results, and why

- **`ok` and `error` on every result.** The agent is told that `ok: false` means "say what you could not check", so a missing id or a database error can never become a made-up answer. The error text names the fix ("use a product_id from search_products").
- **`product_id` on every item.** Ids are the only key the agent may pass to the other tools and the only thing the route accepts for product cards, so every result carries the id next to the name. The agent is told never to invent an id.
- **`name`, exactly as stored.** The prompt says to quote names verbatim; shoppers and the cards match on it.
- **`price` (number) and `price_display` (string).** The number keeps sorting and the post-reply price check exact; the display string ("$68", "$59.99" only when cents exist) removes the model's chance to round or reformat. The prompt says to use `price_display` as-is.
- **`short_description` in search hits, full `description` in `get_product`.** Search is for picking, so a one-line description keeps eight hits small; description questions get the whole text from one id.
- **`colors` as the stored list.** Colour questions ("in pink?") are answered by membership, and an empty list is reported as "colour not listed" rather than guessed.
- **`sizes_in_stock` and `sold_out_sizes` on search hits and stock lookups.** Stock is per size in this shop (145 of 612 size rows are zero), so a yes/no per item is not honest. Both lists are precomputed so the agent cannot mis-sum, and the sold-out list makes the ghost line ("👻 Sold out in M") a straight read.
- **`quantity`, `status`, `label` per size.** `quantity` is the database number; `status` is the rule applied to it (`sold_out` at 0, `low` at 5 or fewer, else `in_stock`); `label` is the sentence to say ("Only a few left (2)"). Giving all three means the model does not re-derive thresholds, and the prompt limits spoken numbers to the "only a few left" case so counts are not blurted for every size.
- **`other_sizes_in_stock` on a single-size check.** When the asked size is sold out, the alternative is already in hand, so the reply can offer it without a second call.
- **`total_matches`, `query_echo`, `sort` on search.** The agent can say "there are 26 crewnecks; here are eight" and knows which order it got, which stops it calling search again for the same thing.
- **`categories` on search.** The seven real categories let the agent redirect a miss ("we do not carry shorts; we do have tees and performance shirts") from data, not from memory.

### 6.3 Guardrails on top of the tools

- **Cards only from tools.** Every product a tool returns is stored in `ChatState.seen`; the route shows cards only for ids in that set, in the order the agent chose.
- **Price check after every reply.** `agent.unverified_prices` scans the reply for dollar amounts and compares them with the prices of products the tools returned this turn. A mismatch is written to the audit log as `price_check` with the amounts, so an invented price is visible in the trail. Percentages such as the coupon's 10% are ignored.
- **Re-check, do not remember.** The prompt forbids answering price or stock from an earlier turn, because stock changes.
- **Sold out is plain.** The prompt requires the ghost marker and the in-stock alternatives, and forbids "might be available" or restock promises. The item page shows the same ghost next to sold-out sizes when Halloween mode is on.

### 6.4 Tests (`tests/test_tools.py`, 7; 43 passing in all)

Price display equals the catalogue price; search hits are real products with prices and disjoint in-stock / sold-out lists; `price_asc` is ascending and capped at eight; a size with quantity 0 in the shipped data comes back as `sold_out` with the label "Sold out" and appears in `sold_out_sizes`; a single-size check matches the inventory row and excludes itself from the alternatives; unknown ids are errors, not guesses; the price check passes a real price, flags an invented one, and ignores "10% off".

---

## 7. Chat search that updates the page (Problem 7)

### 7.1 The contract

`POST /chat` returns `ChatResponse`:

```
{ "reply": "...", "products": [ProductSummary, ...], "stopped_reason": "completed", "flagged": false, "signed_in": false }
```

`products` is the structured list of matches, in the order the agent chose. Each `ProductSummary` is the same shape the Products grid already uses (`product_id`, `name`, `category`, `short_description`, `colors`, `price`, `image_url`, `total_stock`), so the front end can render it with the same card and no second request. The agent never writes this list directly: it returns `product_ids` in its structured output, and the route maps each id to the `ProductSummary` the tools fetched (`ChatState.seen`), dropping anything a tool did not return.

### 7.2 How results reach the page

1. The agent answers a category question by calling `search_products` and returning the matching ids (prompt section "How your results reach the page": every match for a category question, one id for a single-item question, both for a comparison, none for small talk).
2. The route builds `products` from those ids and the tools' data.
3. `ChatPanel` prints the reply and, when `products` is non-empty, writes `{ query, products }` into the app-wide `ChatResultsProvider` (`frontend/src/chat/`).
4. The page reacts:
   - on the **Products page** the grid becomes those items, in the agent's order, with a status line "Showing the 8 items the assistant found for '…'" and a "See all products" control;
   - on **every other page** a strip "The assistant found these N items" is rendered inside the content column under the page content, with a link to open them on the Products page and a Clear button. The strip scrolls into view (instantly under reduced motion).
5. Both places use `ProductCard`, the Problem 3 card: image, name, price, short description, stock word, linking to `/products/<id>`. So a card the chat just put on the page opens the same single-item view as any other (large image, full text, sizes and stock, the Halloween pop-out on open, and a chance of a hidden friend), with nothing special-cased.

The chat panel still lists small cards under the reply for context, but the page is the main surface. A shared link `/products?ids=a,b,c` reproduces the narrowed grid without the chat.

### 7.3 Why this shape

- One card component means one accessibility pass and one detail route.
- The page never trusts the model's prose: ids are validated against tool results on the server, and the front end renders only what the API returned.
- Results live in React state, not the URL or storage, so a reload starts clean and nothing is logged.

---

## 8. Customer memory: history, identity, page context (Problem 8)

### 8.1 How chat history is stored

- Table `chat_messages` (shipped with the data pack, documented in `docs/data/`): `id`, `user_id` (FK users), `role` (`user` | `assistant`), `content`, `products_json`, `created_at` (UTC). Index `idx_chat_messages_user (user_id, created_at)`.
- `POST /chat` writes two rows per turn for a **signed-in** shopper only: the cleaned user text (after the prompt guard) and the assistant reply with the cards it showed as `products_json`. Guests get a working chat with nothing stored; their browser sends back up to ten recent turns for continuity within the visit.
- **Reload on return:** when the chat widget sees a session token (sign-in or page load with a remembered session) it calls `GET /me/activity` and fills the window with the saved turns and their cards. Signing out clears the window. The same rows are listed, downloadable and deletable on the Account page (`DELETE /me/activity`; `DELETE /me` removes everything).
- **Continuity for the agent:** the route loads the last 20 stored turns and passes them as `message_history`, so the model sees the real conversation, not a summary.

### 8.2 What the agent sees about the customer

Identity is taken from the verified session token on the server and placed in the agent's deps (`ChatState`), never from anything typed into the chat.

| Field | In deps | Reaches the model | How |
|---|---|---|---|
| `first_name` | yes | every turn | dynamic instruction: "The shopper is signed in. Their first name is …" |
| `last_name` | yes | only on request | `who_am_i` tool result |
| `email` | yes | only on request | `who_am_i` tool result |
| user id, password hash, provider id, coupon | no | never | not in deps at all |

Decision (the student's suggestion): the prompt carries the first name only. Last name and email reach the model solely when the shopper asks "who am I?" or which account they are using, through the `who_am_i` tool, which answers from deps. That satisfies the acceptance test ("answers with your name and email") while keeping email out of every ordinary turn. The audit trail redacts email addresses in any text it records, and the `who_am_i` tool logs only `ok` and `signed_in`. Guests get "nobody is signed in".

### 8.3 How page context is passed

- The browser adds `page` to every chat request: `{ route, product_id?, product_name? }`. On `/products/<id>` the widget fills `product_id` from the URL. `PageContext` is `extra="forbid"`, the route must match `^/[A-Za-z0-9/_\-.]*$` and the id the product-id pattern, so nothing odd gets in.
- The server **re-reads the product from the database** by id. The agent's deps get our `ProductSummary` (name, price, colours), never the browser's `product_name`, which is accepted only as a hint and otherwise ignored. A verified page product is also added to the "seen" set so it can be a card.
- A dynamic instruction tells the model, per run: who is chatting (first name), the product on screen with its id, price and colours, that "this / it / this one" means that product and must be resolved with `get_product`, `get_stock` or `check_stock` by id, and the list of tools it can call this turn. The prompt file adds the standing rules in "Memory, identity and the page on screen".
- The audit records a `context` line per turn with `signed_in`, `page_route`, `page_product` (id only) and the tool names, never the shopper's name or email.

### 8.4 Tools in deps

`ChatState.tool_names` lists the tools registered on the agent (`search_products`, `get_product`, `get_stock`, `check_stock`, `who_am_i`); `register_tools` asserts the list stays in step, the dynamic instruction repeats it to the model each turn, and the audit's `context` line records it, so a run can always be read against the exact tool set that was available.

### 8.5 Acceptance test

- Sign in, chat, sign out, sign in: the window reloads the saved turns (and the Account page lists them).
- "who am I?": the agent calls `who_am_i` and answers with name and email.
- On a product page, "do you have this in pink?": the agent resolves "this" to the product on screen, checks its colours and stock through the tools, and answers from the database.

Tests (`tests/test_chat.py`, 48 passing in all): history turns grow across a signed-in conversation; `lookup_identity` answers from deps and refuses for guests; a page product is resolved from the database and the browser's name is never used; bad page context is rejected (422); the audit log redacts email addresses.

### 8.6 House style: no em dashes

The student's rule for everything in this workspace: no em dashes. Four layers keep them out of the app: `prompts/prompt.md` tells the agent never to use one; `agent.strip_em_dashes` rewrites any that slip through (a dash between words becomes a comma, an en dash becomes a hyphen) before the reply is stored or shown; `tests/test_hygiene.py` fails if an em dash appears in any of the project's own files; and the workspace rules (`CLAUDE.md`, `Agent.md`) carry the rule for future work. Seeded chat rows from the course data pack are left as shipped.

---

## 9. Usability improvements (Problem 9)

The write-up for graders, with the friction audit, is `output/usability.md`. This section records how each piece is built.

### 9.1 Friction audit

Measured before building: API 3 to 5 ms per request, product list 42 KB, images 35 KB average and lazy-loaded, bundle 130 KB gzipped, so load time was not the problem. Chat turns cost 4.6 s with one tool call and 11.8 s with three, so each model round trip is worth cutting. Clicks were the other cost: two clicks plus a scroll per item to learn a size, no price or stock filters in the UI, a sold-out answer that led nowhere, and a three-step coupon claim for guests. Numbers and the after-measurements are in `usability.md` section 0.

### 9.2 Hidden friends collection (front end 1)

- **Definition in code, not data:** `backend/hunt.py` holds the seasons (Halloween live as a daily set of 31; Thanksgiving and Winter defined, `art_ready=False`), the cast (`CHARACTERS`: Bramble, Dusk, Pip, Whiskerline, Snaggle, Cinder, Hush) and the costumes (`HALLOWEEN_COSTUMES`: witch, ghost, zombie, skeleton, vampire, mummy, pumpkin, devil). `_daily_friends` builds day 1 to 31 by advancing character, costume and home page together, so keys (`<character>-<costume>`) never repeat. Milestones: `COUPON_AT=3` (10%), `LIFT_AT=10` (15%, referrals count), the full set earns the free-item voucher (`FREE_ITEM_MAX_USD=100`, terms in `models.FREE_ITEM_TERMS`), `REFERRAL_CREDIT_MAX=3`. `today()` honours `HUNT_DATE`; `is_available` unlocks a daily friend from its day of the month; `record_find` refuses a friend whose day has not come. `current_season()` picks the most recently started season that has art, so the active set carries on until the next one is drawable; `HUNT_SEASON` in `.env` forces one for a demo.
- **Storage:** `egg_finds` (one row per shopper per season per friend, `source` found or referral, `referred_user_id` for credits), `rewards` (the free item, one per kind per shopper), the existing `coupons` row lifted in place to 15%, and `users.referral_code` / `users.referred_by`. DDL in `data/schema.sql` section 7, applied by `db.ensure_schema()`, which also backfills referral codes for existing accounts.
- **Routes:** `GET /hunt` (public programme, no PII), `GET /me/hunt` (own progress), `POST /me/hunt/finds` (`FindRequest`, extra forbid; 404 for a friend not findable this season). `hunt.record_find` writes the find and runs `_evaluate`, which grants whatever is now earned and never twice; it returns `HuntProgress` with an `unlocked` list the UI turns into dialog text. Signup accepts `referral_code`; an unknown code is ignored, a known one sets `referred_by` and calls `hunt.credit_referral`.
- **Front end:** `hunt/HuntProvider.tsx` loads the programme once, keeps server progress keyed by session token, keeps guest finds in `localStorage` (`cc-hunt-guest`, friend keys only) and banks them with one request per find when a token appears. `eggs/eggs.ts` plans one appearance per page visit: the unfound friend whose home matches the route always appears; otherwise an unfound friend strays with probability 0.35; found friends never reappear. `Layout.tsx` keys the plan on the visit, not on the found set, so a found friend stays put (marked found, disabled) until the shopper moves on. `EasterEgg.tsx` shows the outcome (count, codes just earned, next riddle); `Account.tsx` shows the 31-slot tray (found, out-but-unfound, locked with arrival date), rewards with the voucher terms, referral code and coming sets; `NavBar.tsx` shows "n/31" and a Staff link for staff accounts. `characters.tsx` draws seven base characters, each with costume overlays placed by per-character anchors; an unknown pairing renders a silhouette and a locked day a padlock.
- **Agent:** `hiding_clue` tool (`tools.lookup_clue` -> `hunt.clue`) returns the next riddle and progress; the prompt's "Hidden friends" section lists the only numbers the agent may quote and tells it to send shoppers to `/account` for codes.

### 9.3 Products you can narrow (front end 2)

`ProductQuery` gained `sort` (relevance, price_asc, price_desc, name), applied in `db.list_products`, so the API, the page and the agent's `search_products` share one implementation. `ProductSummary` gained `sizes_in_stock`, computed for the whole grid with one extra query over `inventory`. `Products.tsx` reads every filter from the URL with `useSearchParams` and writes changes back (a new filter clears the assistant's `ids` list); `ProductCard.tsx` renders the chips with visually hidden "in stock / sold out" text.

### 9.4 Restock requests (agent and back end 1)

- **One rule set, two doors:** `tools.create_restock(user_id, product_id, size)` is called by the agent tool `request_restock` and by `POST /me/restock-requests` from the item page. It refuses for guests, unknown products, sizes not offered, sizes with stock, and more than ten open requests; it returns `RestockResult` with `outcome` created or already_open. Table `restock_requests` with a partial unique index on open rows (so a cancelled request can be re-filed).
- **Shopper side:** `GET /me/restock-requests`, `DELETE /me/restock-requests/{id}` (own rows only), listed on the Account page with Cancel.
- **Staff side:** `ADMIN_EMAILS` in `.env` (comma-separated); `current_admin` dependency returns 403 for everyone else; `GET /admin/restock-requests` groups open rows by product and size with the requesters' names and emails (a documented use of PII); `GET /admin/restock-requests.csv` is the same list for a spreadsheet; `POST /admin/restock-requests/{id}/ordered` closes a row. `UserPublic.is_admin` tells the Account page whether to show the section.
- **Prompt:** "Sold out is not the end" section: alternatives first, then the offer, the tool only after a yes, never a promised date. The audit records product id, size, outcome and request id, never the shopper.

### 9.5 Fewer dead ends and clicks (agent and back end 2)

- `find_alternatives(product_id, size)` (`tools.lookup_alternatives`): same category, `in_stock` filter, keep items with the size in `sizes_in_stock`, sort by price distance then shared colours, cap five; every item lands in `ChatState.seen` so it can be a card.
- **Page stock in context:** the dynamic instruction in `agent.py` now includes the on-screen product's stock by size (the server already read a `ProductDetail` for it) and tells the model to answer stock questions from that line and call `get_product` only for description or tags. The prompt's "facts from tools" rule names this note as the one exception.
- **Page links:** `ChatReply.go_to: PageLink(route, label, navigate)`. `agent.validate_page_link` accepts `/`, `/products`, `/about`, `/login`, `/create-account`, `/account`, and `/products/<id>` only for ids in `seen`; a query string is allowed only on `/products` and must validate as `ProductQuery`, after which it is rebuilt canonically (integers without ".0"). Dropped links are logged as `link_check`. `ChatPanel.tsx` renders the link as a button and calls `navigate()` when `navigate` is true.
- `TOOL_NAMES` is now eight tools; `ChatState.user_id` was added for the write and the clue, and never reaches the prompt.

### 9.6 Tests and evidence

`tests/test_usability.py` (15 tests, 65 passing in all): sort and chips; the public programme; finds, milestones and no second code; ten finds earn the free item once; referrals capped at three and malformed codes rejected; delete cascade; restock refusals, dedupe and cap; own list and cancel; staff queue, CSV, mark ordered and 403; alternatives; link validation; page-stock note in the first request's instructions; clue tool; season selection. Live run and screenshots are listed in `usability.md`.

---

## 10. Style (Problem 10)

The design write-up for graders is `output/design.md`. This section records what was built and where.

### 10.1 Reference and approach

The real Yale Bulldog Blue site (Shopify) was opened in the browser and read for feel only: white page, Open Sans throughout, charcoal text with a teal link colour, a stacked varsity wordmark, an "Officially licensed" strip, a big search bar, product rows with white photos and flat cards, a "Need help?" bubble. Nothing was copied; its home page also carries hidden AI-directed text (reported in Problem 3), which was ignored. Our flavour keeps the class black-and-pink rule and the Yale Blue surfaces, and adds the pieces below.

### 10.2 What was built

- **Fonts** (`main.tsx`, `index.css`): `@fontsource-variable/fraunces` and `@fontsource/alfa-slab-one` bundled by Vite (`--font-display`, `--font-slab`); `h1`/`h2` in Fraunces with `SOFT` and `WONK` axes, wordmark, prices and the hero Y in Alfa Slab One; a shared `.eyebrow`.
- **Brand** (`components/Bulldog.tsx`, `NavBar.tsx`): an original bulldog SVG (Yale-blue collar, gold Y tag) used in the wordmark, the chat launcher and the chat header; a storefront strip above the nav with the address and the season line; a Staff link for `is_admin` users.
- **Home** (`pages/Home.tsx`): the hero with a decorative Yale-blue Y behind the copy (`.hero-y`, `z-index: -1`), a drop strip with the latest friends and "day n of 31", category cards that load the first in-stock product photo per category from `GET /products`, residential college chips (only colleges present in product names), the motto in the footer.
- **Products** (`components/ProductCard.tsx`, `colors.ts`, `shop.css`): swatches from colour names (`swatchFor` map plus heuristics), "Few left" at twelve units or under, "Sold out" badge, hover lift and photo zoom, stagger via `--i`; `pages/ProductDetail.tsx` gets sticky details, large swatches and "Ask the bulldog about this item" (a `cc:ask` window event that `ChatPanel` listens to, opening the counter with the draft filled).
- **Chat** (`ChatPanel.tsx`, `shop.css`): bulldog avatar and launcher, "The shop counter" header, bubble tails, animated typing dots with hidden text, suggested-question chips on a fresh conversation, message ids from a ref (no impure calls in render).
- **Scene** (`halloween/HalloweenScene.tsx`): Harkness Tower (stages, pinnacles, lit clock, glowing lancets) and Evans Hall (roof slab, glass front with eleven lit panels, thirteen fins, plaza glow, small "EVANS HALL" label) replace the house; the dead tree moved to the left edge.
- **Motion** (`index.css`, `shop.css`): `.page-enter` keyed by route in `Layout.tsx`, `card-in` stagger capped at eleven steps, hover transforms, typing dots; all inside `prefers-reduced-motion: no-preference`.
- **Staff page** (`pages/Staff.tsx`): the restock queue, CSV and "Mark ordered" moved out of the Account page; the page explains the `ADMIN_EMAILS` rule, non-staff get a plain message, and the Account page shows a Role line.
- **31-day set** (`backend/hunt.py`, `eggs/characters.tsx`): seven characters with anchor-placed costume overlays; see section 9.2 for the rules and `usability.md` for the ladder.

### 10.3 Checks

`npm run build` and `npm run lint` clean; 66 back-end tests passing (hunt tests pin `HUNT_DATE=2026-10-31`); contrast pairs and motion gating recorded in `docs/accessibility.md`; the fonts add 130 KB of woff2 to the bundle and no network request.

---

## 11. App check (Problem 11)

`output/app_check.html` is a self-contained page (double-click to open; inline CSS, no scripts, no external resources) with four figures from `output/app_check_images/`, linked by relative path: `inventory.jpg` (chat quotes stock and price for the item on screen, cross-checked by SQL: M = 5 units, $68), `hoodie-cards.jpg` (eight hoodie cards in the chat and on the Products grid after a category question), `sold-out-alternatives.jpg` (the Problem 9 feature: ghost for a sold-out XL, five alternatives with XL in stock, the restock request link) and `filters-chips.jpg` (bonus: URL-backed filters and size chips). Each check has a heading, the screenshot, a one-or-two-sentence caption and a "proves" line with the database query behind it. The checks were run against the live site with the real model; the audit trail records the tools used per turn.

---

## 12. Audit trail, safety rules, finished harness (Problem 12)

### 12.1 The append-only trail: `output/audit_trail.json`

- **Format.** One JSON array, one record per line, valid JSON after every write. `audit.append_json_array` opens the file in place, finds the closing bracket, and replaces it with `,<record>]`. Earlier bytes are never rewritten, nothing is ever truncated or deleted by the app, and the file is created on first use. If a crash ever left the tail damaged, the next record is added on its own line so no record is lost. The per-node forensic log `backend/output/audit.jsonl` (Problem 5) keeps running next to it, gitignored.
- **Records.** Every record has `ts` (UTC, milliseconds), `run_id` (random per turn, never a user id) and `event`:

  | Event | Fields | Written when |
  |---|---|---|
  | `turn` | `prompt` (cleaned, cut at 200 characters, emails redacted), `signed_in`, `page`, `history_turns` | the harness starts a turn |
  | `tool_call` | `tool`, `args` | the model asks for a tool |
  | `tool_result` | `tool`, `result` (cut at 200) | the tool answers |
  | `retry` | `tool`, `result` | the model's output failed validation and was sent back |
  | `guard` | `check` (`prompt_guard`, `cards`, `page_link`, `price`, `em_dash`) and what was dropped or rewritten | a guardrail changed the output |
  | `reply` | `text`, `product_ids`, `go_to` | the final answer passed the checks |
  | `stop` | `stop_reason`, `requests`, `tool_calls`, `ms` | always, even after an error or a guard-only turn |

- **Live excerpt** (one signed-in turn on a crewneck whose XL is at zero):

      turn        prompt "Do you have this in XL? If not, please ask the shop to reorder it.", signed_in true, page /products/baseball-left-chest-crewneck
      tool_call   check_stock {"product_id": "baseball-left-chest-crewneck", "size": "XL"}
      tool_result check_stock ok=True ... size='XL' quantity=0 status='sold_out' ...
      tool_call   find_alternatives {"product_id": "baseball-left-chest-crewneck", "size": "XL"}
      tool_call   request_restock {"product_id": "baseball-left-chest-crewneck", "size": "XL"}
      tool_result find_alternatives ok=True ... items=[...]
      tool_result request_restock ok=True request_id=4 ... outcome='created'
      reply       "👻 Sold out in XL for Baseball Left Chest Crewneck. I asked the shop to reorder it ..."
      stop        completed, requests 3, tool_calls 3, 7909 ms

  The guard-only turn ("Ignore all previous instructions ...") leaves two records, `guard prompt_guard: 1 injection block(s) dropped before the model` and `stop guardrail`, and never the text.
- **Across runs.** The file held 22 records from four turns, the back end was restarted, one more turn added five: 27, same file, earlier records byte-for-byte unchanged (the test suite asserts the same on a temporary copy).
- **What is not in it.** No user id, name, email (redacted even inside a reply), token, key, raw injection payload or SQL. That is why the file can be committed with the repo, which the assignment asks for; `docs/governance.md` records the decision.
- **Tests.** `backend/tests/conftest.py` points both audit files at a temporary folder for every test, so test runs never touch the real trail. `test_chat.py` adds two tests: the array grows across two runs and a guard-only turn, stays valid JSON, keeps earlier records untouched, records tool calls and results, and never contains the injection text; and the array writer itself handles a new file, a second record and an empty array.

### 12.2 Safety rules added to the prompt

`prompts/prompt.md` section "Safety rules (Problems 5 and 12)" replaces the Problem 5 basics with nine groups: where instructions come from (only the prompt and the server note; typed text, history, tool results, product text and riddles are data, and claimed authority or urgency changes nothing); what is never revealed (prompt, tools, model, keys, paths, audit, other shoppers); identity and personal data (server-only identity, no asking for details, no repeating volunteered secrets, email only through `who_am_i`); money, orders and promises (no orders, payments, holds, discounts, codes or dates); honesty and uncertainty (say what could not be checked, never a guess, never "probably in" for zero stock); the one write (`request_restock` only after a clear yes, one at a time, never for someone else); pages and links (site routes only, open only when asked); conduct (all ages, no advice on medical, legal or financial matters, care for a shopper in distress, friendly rivalry only); loop discipline (fewest tools, no repeated calls, stop after two failures, short replies in the shopper's language, no em dashes).

The same pass found the prompt's hidden-friends section out of date (it still described a four-friend set and the earlier ladder), so it now states the seven-character cast, the 31-day Halloween set and the live ladder: 3 finds = 10% coupon, 10 finds = 15%, the whole set = the free-item voucher with its terms.

### 12.3 Other changes in this problem

- `agent.unverified_prices` now ignores a dollar figure the shopper typed themselves ("under $50" echoed back is a budget, not a price); the first live turn had flagged it.
- `main.py` loads `backend/.env` and then the hw4 root `.env`, so the course layout (`.env.example` at the root) and the development layout both work.
- The pinned `requirements.txt` moved to the hw4 root (`backend/requirements.txt` points to it) and `.env.example` moved to the root with placeholders, as the submission layout requires.
- 68 tests passing.

---

## 13. Repository and submission (Problem 13)

- **Repo:** `https://github.com/lukepfaffyale/hw4`, public. Cloning it gives a folder named `hw4` with the layout the assignment lists: `AI_prompts.md`, `requirements.txt`, `.env.example` (placeholders only), `.gitignore`, `README.md` (the five run steps), `frontend/` (Vite + React + TypeScript), `backend/` (`main.py`, the four agent files `prompts/prompt.md`, `agent.py`, `tools.py`, `models.py`, and the web app modules around them), `output/` (`harness.md`, `design.md`, `usability.md`, `app_check.html`, `app_check_images/`, `audit_trail.json`), plus `docs/` (data dictionary, models, governance, accessibility, screenshots).
- **Never committed** (`.gitignore`): `.env` at the root and in `backend/`, `data/` (the database and the product photos), `node_modules/`, `__pycache__/`, `venv/` and `.venv/`, `frontend/dist/`, `backend/output/` (the per-node audit log and the prompt-guard flags), and `RESUME.md` (working notes). The back end runs on port 8000 and the front end calls `http://localhost:8000` by default.
- **Checks before the first push:** 68 tests, `npm run build` and `npm run lint` clean; a grep over the project for the course landmine markers (none in tracked files), secret-looking strings (none), key values (only inside the ignored `.env`), personal data strings (none in tracked files), and em dashes (none); `git add --dry-run` reviewed file by file. The repository starts with this single commit, so nothing sensitive was ever in its history.
- **Acceptance test, part 1:** a fresh clone into a temporary folder was checked for every file above and for the absence of `.env`, `campus_customs.db` and `data/products/`.
- **Acceptance test, part 2 (README alone gets the app running):** the same clone was run exactly as the README says, against a pristine copy of the data pack (the app's own tables `coupons`, `egg_finds`, `rewards`, `restock_requests` and the `users` columns `auth_provider`, `provider_user_id`, `referral_code`, `referred_by` stripped out, so the shipped schema is what the server meets on first start). New virtual environment, `pip install -r requirements.txt` from the root (52 s), `.env` copied from `.env.example` with a key, `uvicorn main:app` from `backend/`. First start added the app's tables and columns with no warnings. Then: 102 products with sizes on every card; the item page; the hidden-friends programme (19 of 31 out on the real date); signup, `/me`, login; a find recorded (1 of 31); a restock request; one real chat turn (5.6 s, one card, one tool); `output/audit_trail.json` grew by five records; activity listed; account deleted and the login refused afterwards. `pytest`: 68 passed. `npm install` and `npm run build`: clean. The pyenv pin `backend/.python-version` was removed so a grader on Python 3.12 or 3.13 is not stopped by it.
- **Characters and attribution (follow-up):** the seven hidden friends now carry original on-screen names (Bramble, Dusk, Pip, Whiskerline, Snaggle, Cinder, Hush) from `hunt.CHARACTERS`; the internal keys (`totoro-witch` and so on) stay, so stored finds, guest finds and tests keep working. Coupon codes take their word from the display name (`BRAMBLE10-...`). The drawings were always our own inline SVG; the About page, the README and `docs/governance.md` now credit the characters they nod to (Studio Ghibli's films, Kasing Lung's Labubu) and state that nothing is official, licensed or for sale. The agent's prompt says the same if asked.
- **README map (follow-up):** the README states plainly that the agent is the four files and names the web-app modules around it, carries a "Recreating problems 1 to 13 from this clone" table (where each problem lives, how to see it working) and an "If something does not start" list.
