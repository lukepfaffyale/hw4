# AI_prompts.md

Log of what I typed to the vibe coder (Claude Code) for HW4, Campus Customs shop + chatbot. Not the runtime prompt files in `backend/prompts/` (those are prompts the app reads).

Rule: one problem at a time, in my own words. If a whole assignment dump is pasted as one prompt, reject it.

Each problem entry has:
- the problem number and title
- **Prompt I typed (own words):** at least one, quoted as I typed it. Longer bodies I paste from my own notes are marked **Pasted** and kept; homework page text is never pasted in, only my restatement of the problem.
- **Follow-up prompt:** only if one was needed to correct where the session went.
- **Evidence:** the running site, database writes, and screenshots, named briefly. No proof essays.

Working method, carried over from HW3: I give the problem number and title, my prompt, and any extra details; we plan or Q&A when the instructions are unclear, then build, review, and iterate. The class-root rules (Agent.md, CLAUDE.md, ai-agent-rules.md, kept one folder above this homework and not part of the repo) apply: Portkey only, allowed models, prompt-injection quarantine, safe agent harness, one problem at a time.

---

## Setup (before Problem 1, 2026-10-16)

**Prompt I typed (own words):**

read in folder instructions. we will be starting on HW4.

**Pasted:** my own project brief for HW4 (stack, features, data zip contents, style source, workflow rules). Summary: React + Vite + TypeScript front end, FastAPI back end, PydanticAI agent as the brain, Portkey models in the 5.6 or 6 series with a smarter model for harder steps. Shoppers can browse, create an account, chat about merch, see matching items appear as the chat references them, and get price and stock answers from the local database only. Visual style and prompt facts researched from yalebulldogblue.com. Final step is a public GitHub repo submitted on Canvas. Database and product images are gitignored. I also gave the path to the data zip.

**Follow-ups I typed:**

- we'll utilize our global harness. not seeing it in the folder but maybe its in one of the .md, or in one of the HW we already submitted
- ok yes, lets create the folder as HW4 for now.

**What happened:** rules read; zip extracted into an isolated scratch folder and inspected (catalogue 102 rows, inventory 612 rows, users 3 rows with PBKDF2 hashes, plus a `chat_messages` table the brief did not mention); every text cell and image scanned for landmine and injection markers, none found; harness located in `Lecture4/stock_agent/`, `Lecture 5/prompt_guard.py`, `HW3/llm.py`. `HW4/` created with the data copied in and `.gitignore` excluding the database and images.

**Evidence:** `HW4/data/` present locally, `HW4/.gitignore`. No code yet.

---

## Problem 1: Create AI_prompts.md

**Prompt I typed (own words):**

Problem 1: create AI_prompts.md and we'll keep it updated as we work. As prior, this file is the log of what we discuss and what i type. Before we create, if I paste in text, would the log capture that as pasted or typed?

**Follow-up prompt:**

ok rest of P1, seems to be the same pattern as prior HW P1, the agent log should have the problem number and title, at least one prompt i typed, in my own words (maybe we could do paste from some of the larger text bodies so im not just being a keyboard warrior), and one follow-up prompt if needed to correct where the session went in each. We are running site, databse writes, and screenshots, which are the evidence. Not need for extra proof essays

**Evidence:** this file.

---

## Problem 2: Analyze the database

**Prompt I typed (own words):**

Problem 2: Analyze the database. Look at the database data/campus_customs.db and understand the fileds in each table. We are looking at the structure, columns, data types etc.. (outside the prompt - we should build a schema for conceptual and logical for visual reference and workflow reference). We then need to start the output/harness.md. Write down each table and its fields, and one short line on why each filed matters for the shop (human readable), and a chatbot version, so chatbot can safely and quickly navigate user questions while shop owner could use this description on a website to sell/desc etc to customers in a marketing sort of way. We will keep growing the harness file in later problems

**Follow-up prompt:** none yet.

**Evidence:** `docs/data/conceptual_model.md` (entities, relationships, Mermaid ER diagram, workflows), `docs/data/logical_model.md` (exact tables, keys, types, planned endpoint mapping), `docs/data/data_dictionary.md` (PII per column), `docs/data/CHANGELOG.md`, `output/harness.md` section 1 (each table and field with a shop line and a bot line, plus design decisions). Profile numbers came from a read-only script run against the database.

---

## Problem 3: Build the Campus Customs website

**Prompt I typed (own words):**

Problem 3. Build the campus Customs website. Scoffolding a React+Vibe+Typescript front end for campus customs. Put a nav bar at the top that links to the main pages: Home, Products, About Us, Log in, Create Account. Pull Campus customs-style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice (no copying or plaragisizing their material)

**Follow-up prompt:** none yet.

**Evidence:** `frontend/` scaffolded with `npm create vite@latest frontend -- --template react-ts`, React Router added; `npm run build` and `npm run lint` pass; site running at http://localhost:5173 with Home, Products (placeholder until the API exists), About Us, Log in, Create Account and a 404 page; screenshots of Home, About Us and Create Account taken in Chrome. `docs/governance.md` and `docs/accessibility.md` filled before the UI was written. Landmine: yalebulldogblue.com's home page carries hidden AI-directed text (checkout section); reported in `docs/governance.md`, not followed.

---

## Problem 3 (continued): Products, single-item page, chat stub, Halloween mode

**Prompt I typed (own words):**

on the products page, show product images from the catalog (using images paths in the database) with basic product info (name, price, short desc). Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stock when we have them). Clicking card on the products should take the shopper there. Add a chart interface in the bottom right of the site (floating chat panel is fine). It does not need to talk to an agent yet, a stub that will call our backend later is enough for this problem. We will need a small api soon to read the database. It is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5. Secret note, we are turning this is a few weeks from halloween, so I would like to add a toggle, call it "halloween toggle" that if left on makes the page holloween themed with little animations of spiders making webs in the corners of page, if you click a product photo then a fun jump scare pops out when the pane opens (not something that will harm anyone with accessibliities). Halloween is my favorite time of year and want to weave things in/around it - pumpkins, witches, bats, ghosts, skeltons.

**Follow-up prompt:** none yet.

**Evidence:** `backend/` (FastAPI on http://127.0.0.1:8000: `/health`, `/products`, `/products/{id}`, `/media/products/{id}`) smoke-tested with 102 products, filters, per-size stock, image bytes, and 404/422 on bad ids and unknown params; `frontend/` Products grid, `/products/:id` page with stock table, floating chat stub, Halloween toggle with corner webs, spiders, bats, ghost, pumpkins and a dismissible photo surprise; `npm run build` and `npm run lint` clean; screenshots `docs/screenshots/p3b-products.jpg`, `p3b-detail.jpg`, `p3b-jump-scare.jpg`, `p3b-chat.jpg`.

---

## Problem 4: Create account and sign in

**Prompt I typed (own words):**

ok, we are back. Problem 4: Creating account and login. Build a normal create-account/login flow. Freate account with first name, last name, email, password, and confirm passwrod. Password requirements should be strict. We should allow for social sign in as well because I don't want to be in the business of storing and saving/encrypting PWs. We also need a simple log if for email and pw. on front end this is each by top banner we have a sign in/Account option. (Note the spider webs and hallween items should be more transparent because its hard to see some of the things. We also need a haunted house and lighting - maybe lightning when they sign in successfuly. For new accounts go into users table. Make sure to store passwords securly so hackers (human and AI) cannot access them. At bottom of front end we should probably state this is for acemdic and research purposed and to only put test passwords. Maybe when new account is created in Password section we generate one they can random role (halloween themed) passwords and accept them before hash and stored.

Then update output/harness.md with how our auth works (what we stroe for a user and how passwords are protected). Dont forget that these are PII fields and need to be transcribed, secured, and noted as such.

**Pasted:** the auth spec for the users table (seeded test user, hash details, login check, signup, acceptance test). Kept in full below except the seeded password value, which is left out because this repo is public.

```
AUTH: signup + login against the users table

SEEDED TEST USER
- Email: test@campuscustoms.yale.edu
- Password: (the seeded test password from the course spec; not written here)
- Hash: PBKDF2-HMAC-SHA256, 120,000 iterations
- Stored format: pbkdf2_sha256$salt$hash

LOGIN CHECK
- Never un-hash the stored value. Re-hash what the user typed and compare.
- Split the stored string on $ and read the salt from the middle piece. Do not generate a new salt at login.
- Hash the typed password with that same salt and 120,000 iterations, then compare to the stored hash using a constant-time compare (hmac.compare_digest).
- Inspect the seeded test user's stored string first to confirm how salt and hash are encoded (hex vs base64, salt used as raw string vs decoded bytes) and match it exactly.

SIGNUP
- Generate a new random salt per user
- Use the same function, same salt handling, same encoding, same 120,000 iterations as login
- Store in the same pbkdf2_sha256$salt$hash format
- If signup and login settings differ, even the correct password will fail

ACCEPTANCE TEST
- Log in as the seeded test user: succeeds
- Create a brand-new account in the app, then log in with it: succeeds
- Wrong password on either account: fails
```

**Follow-up prompt:**

Haunted house needs to look way more sppoky with grave yard, crows, moon. the location of the hauted house also makes the text overlayed on top hard to read so... all the halloween effects needs to exist where text is not.. for the lighting, is there any way to get a good light weight lighting effect/gify?

(Result: the house, graveyard, crows, moon, dead tree, fence, pumpkins, ghost and fog became an inline-SVG night scene that is its own band between content and footer, under the heading on the Account page; fixed webs, bats and ghost now only appear in the side gutters at 1460px and wider; lightning is an SVG bolt with glow and flicker, no GIF.)

**Follow-up prompt (Easter eggs):**

lets also sneak in little easter eggs here and there, where randomly a labubu or totoro could be seen across any of the pages. if they click it then maybe it'll give the would be user a 10% coupon code?

10% off coupon is one time only per user and only for one item

(Result: a drawn Totoro or Labubu appears on about a third of page visits in a text-free spot; activating it claims the shopper's single 10% coupon for one item, enforced by a `coupons` table with one row per user; guests are asked to sign in and the claim finishes on the Account page; `?egg=totoro` forces one for testing.)

**Evidence:** `backend/tests/test_auth.py` (28 tests: hash never equals plaintext, both hash formats verify, weak passwords rejected, tokens tamper-proof, seeded user logs in, new account signs up then logs in, wrong password fails on both, 422 never echoes the password, per-email rate limit, delete account); a new account created through the site with a rolled password and visible in the `users` table as a bcrypt hash (row 4); screenshots `docs/screenshots/p4-signin.jpg`, `p4-create-account.jpg` (roller and live rule checklist), `p4-account.jpg`, `p4-scene-lightning.jpg` (seeded user signed in, night scene with lightning under the heading), `p4-easter-egg.jpg` (Totoro on a product photo, guest asked to sign in); a `coupons` row for the seeded user after the claim finished on the Account page; `output/harness.md` section 4.

---

## Problem 5: PydanticAI agent back end

**Prompt I typed (own words):**

Problem 5: PydanticAI agent backend. Build the shop chatbot as a PydanticAI agent behind fastapi, plugged into our front end chat widget (easter eggs can apply here too - does not have to be coupon event) Put the api app in backend/main.py, that is the file we run with Uvicorn. Keep the agent as these four files next to it (same ideas as HW3).

Lastly, put campus customs voice and safty basics into prompts/prompt.md (we will exapnd tools and saftey in the next few problems). Start or update types in models.py for chat replies/product cards as needed. In output/harness.md, note how the front end tlks to FastAPI and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000

**Pasted:** the agent file-structure spec (four files beside main.py, chat route, config from `.env`, acceptance test: a message from the website chat gets a reply; product and auth routes still work). Kept in full:

```
AGENT: backend file structure + chat route

FILES
- backend/prompts/prompt.md: system prompt (keep growing this same file later, do not split it)
- backend/agent.py: agent entry point and wiring (loads prompt.md, sets model, registers tools)
- backend/tools.py: tools the agent can call
- backend/models.py: Pydantic / PydanticAI structured types

main.py (FastAPI)
- Expose a chat route: website sends a message, route returns the agent's reply
- Keep or add the routes needed for products and auth (signup, login)

CONFIG
- Agent needs the AI model API key (PORTKEY_API_KEY or equivalent)
- Load it from a .env file, never hardcode it
- Add .env to .gitignore so the key is not committed to the public repo

ACCEPTANCE TEST
- Send a message from the website chat, get a reply from the agent
- Product and auth routes still work
```

**Follow-up prompt:** none yet.

**Evidence:** `backend/{agent,tools,models,main}.py` + `backend/prompts/prompt.md` (+ `audit.py`, `prompt_guard.py`); `backend/tests/test_chat.py` (7 tests on PydanticAI's TestModel: reply, cards only from tool results, signed-in memory stored and deleted, injection flagged without payload, audit trail, bad payloads, product and auth routes still work); a live reply from `gpt-5.6-luna` through Portkey from the website chat with product cards; `backend/output/audit.jsonl`; screenshot `docs/screenshots/p5-chat.jpg`; `output/harness.md` section 5.

---

## Problem 6: Tools for product info and stock

**Prompt I typed (own words):**

Problem 6: Tools: product info and stock. We are going to give the agent tools to access and lookup real info from campus_customs.db. Product desc, price, how many are in stock. The agent must use the databse, it should not invent prices or quantities. If a size is out of stock, say so clearly (maybe use ghost) ;). Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py. in output/harness.md, list each tool and explain which model fields we chose for lookup results and why,

**Follow-up prompt:** none yet.

**Evidence:** `backend/tools.py` (four tools: `search_products` with a price sort, `get_product`, `get_stock`, `check_stock`, each over a unit-tested `lookup_*` function), `backend/models.py` (`ProductBrief`, `SearchResult`, `ProductResult`, `SizeStock`, `StockLookup`, `StockResult`), `prompts/prompt.md` "Tools and when to call them" table with the 👻 sold-out rule, `agent.py` post-reply price check logged as `price_check`; `backend/tests/test_tools.py` (7 tests, 43 passing in all); a live chat asking about a sold-out size answered from the database with the ghost; `output/harness.md` section 6.

---

## Problem 7: Chat search that updates the page

**Prompt I typed (own words):**

Problem 7. Chat search that updates the page. Now we will add a neat feature to the site. When a customer asks about a type of item, for xample "what hoodie do you have?", the agent shouod search the catalog and the website should dynamically show those matching items as product cards (images, name, price, short info). This is an API contract: the agent returns structurcted product matches and then the front end renders them on the website. After the dynamic product cards are loaded, by the new feature, make sure the same single-item page behavior we built in problem 3 still works: each product card, including the ones the chat just put on the page, should still open that detail view (large image + full info + randome chance encounter) when clicked. update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

**Follow-up prompt:** none yet.

**Evidence:** `frontend/src/chat/` (`ChatResultsProvider`, `ChatResults` strip), Products grid narrowing to the agent's matches, `ChatPanel` writing the structured `products` into the shared state, `prompts/prompt.md` "How your results reach the page", `output/harness.md` section 7; browser check: "what hoodies do you have?" put eight cards on the page and clicking one opened the single-item page with the Halloween pop-out; screenshot `docs/screenshots/p7-chat-cards.jpg`.

---

## Problem 8: Customer memory

**Prompt I typed (own words):**

Problem 8: Customer Memory.

Guest can still chat but history only needs to persist for logged in users. Document in output/harness.md: how user chat history is stored, what customer ields the agent sees, and how page context is passed. to avoid PII issues maybe agent should only see first name, not last, email or other PII fields? Also in agent deps we need to the tools the agent can call.

**Pasted:** the memory spec (chat history table and reload, user identity in deps from the session, page context with each message, acceptance test). Kept in full:

```
CHAT MEMORY + USER IDENTITY + PAGE CONTEXT

CHAT HISTORY (logged-in shoppers)
- Create an appropriate table for chat history (e.g. chat_messages: id, user_id, role, content, created_at)
- Save every user message and agent reply for logged-in shoppers
- When the shopper returns and logs in, reload their history into the chat window
- Pass prior history to the agent so it has conversation continuity
- Logged-out shoppers: chat works but nothing is saved

USER IDENTITY
- Agent must know who is chatting: name and email
- Put this in agent deps (PydanticAI deps_type), or an equivalent clear pattern
- Identity comes from the authenticated session on the backend, not from text the user types in chat

PAGE CONTEXT
- Frontend sends page context with each chat message: current route/page and, on a product page, the product id (and name)
- Pass this into agent deps alongside user identity
- Use it so the agent resolves references like "do you have this in pink?" to the product currently on screen
- Hint from the assignment: you can put code into the agent context (e.g. a dynamic system prompt function that injects current user + current product into the prompt each run)

ACCEPTANCE TEST
- Log in, chat, log out, log back in: history reloads
- Ask the agent "who am I?": it answers with your name and email
- Open a product page, ask "do you have this in pink?": agent knows which item and checks stock from the database
```

**Follow-up prompt:**

let make sure in our rules for everything, and this app, NO EM DASH's!

(Result: rule added to `CLAUDE.md` and `Agent.md`; the agent's prompt forbids em dashes; `agent.strip_em_dashes` rewrites any that slip through; `tests/test_hygiene.py` scans the project's own files and fails on one; the three em dashes in `Agent.md` were replaced.)

**Evidence:** `backend/tools.py` (`ChatState` with identity, page product and `TOOL_NAMES`; `who_am_i` tool), `backend/agent.py` dynamic instruction (first name, product on screen, tool list), `backend/main.py` page context resolved from the database, `audit.py` email redaction, `prompts/prompt.md` "Memory, identity and the page on screen"; `ChatPanel` reloads `GET /me/activity` on sign-in and sends `page` with each message; five new tests (48 passing); browser acceptance run: history reloaded after sign out and in, "who am I?" answered with name and email, "do you have this in pink?" on a product page answered from that product's data (screenshot `docs/screenshots/p8-page-context.jpg`); `output/harness.md` section 8.

---

## Problem 9: Usability improvements

**Prompt I typed (own words):**

Problem 9: Usability improvements. Now that the core shop is in place they want us to choose and implement 2 front-end usability improvents and 2 agent / backedm useablilty improvements. Front-end improvemtns are things that make the site look better and make it easier to use. Agent/backend improvemnts are things that make the agent output better, more accurate or safr. These could be new agent tools or things that make the agent run faster or cheaper. I feel we've done this along the way but lets discuss ideas. Then we'll write to output/usability.md before or as we build. for each improvement say: what we added, then state why it helps a campus customs shopper or the business. Then make sure all improvements actually show up in the running app. graders will read the write up and look for these features. Two ideas, 1) i think the longer shoppers spend on the site the more engaged they can be and more likely they'll buy something. We could leverage the easter egg as sort of a "chase me here, chase me there, then find my hiding spot" as they navigate from pages and other things so they get the coupon. We should help with return users to get coupon where if they find three or four different random ones (collecting them like cards or something) then they can redem them for a coupon or free shirt or something. Another idea is if we are out of stock and a customer is willing to wait, then the bot can create an order request for product and size so when admin logs in they can easily see what needs ordering and for whom?

**Follow-up prompt:**

love idea 1. We can create holiday variants as the site moves through time for ppl to collect, so halloween themed collectables now and later different versions like thanksgiving, christmas etc.. Again the aim is to give me something to engage, come back, and feel rewarded. collecting 10 or something can be a redeemable free item of $100 or less maybe. Friend referals also become a mechanism. Idea is to keep them connected and engaged while on the site while not being too crazy on it being a game mechanic or drfiting tofar away from being a ecommerce store. Agree on front end pick 2 thats a front and backend. Agree on backend pick. We could also, do a quick bottleneck analysis to see where a user might experence friction the most from load times, clicks, etc.. and then help to cut them? maybe the agent can give clues/riddle to hiding spots or help take the user to pages and reduce clicks?

**Follow-up prompt (characters):**

for the characters we can have labubu and totoro in variations of ghosts, withces, zombies, skeltons etc.. think of them as wearing trick or treat kids costums. Same for soot spiirits and no face

(Result: the cast is always Totoro, Labubu, a Soot Sprite and No-Face in that season's trick-or-treat costumes; the Halloween set became six friends: Witch Totoro, Ghost Labubu, Skeleton Soot Sprite, Zombie No-Face, Vampire Totoro and Mummy Labubu, each drawn as the base character plus a costume; Thanksgiving and Winter sets reuse the same four in holiday costumes.)

(Result: a friction audit first (API and images fast; chat round trips and clicks were the cost), then four improvements. Front end: the hidden-friends collection (Halloween set of six costumed friends, home pages and riddles, three finds earn the coupon, the full set lifts it to 15%, ten finds across seasons earn a free item up to $100, referrals count up to three, guest finds banked at sign-in, Account page tray and nav badge) and a Products page with sort, max price, in-stock-only and size chips on every card, all in the URL. Agent and back end: restock requests (the agent's first write tool, the item page button, the shopper's own list, a staff queue and CSV for `ADMIN_EMAILS`) and fewer dead ends and clicks (sold-out alternatives tool, the on-screen product's stock placed in the agent's context so no tool round trip is needed, validated page links the agent can open, a clue tool for the riddles). Write-up in `output/usability.md`.)

**Evidence:** `output/usability.md` (friction audit with numbers, the four improvements, where to see each); `backend/hunt.py`, `backend/tools.py` (`find_alternatives`, `request_restock`, `hiding_clue`), `backend/agent.py` (page stock in the dynamic instruction, `validate_page_link`), new routes in `backend/main.py`, `backend/data/schema.sql` section 7; `frontend/src/hunt/*`, `eggs/*` reworked, `pages/{Products,ProductDetail,Account,CreateAccount}.tsx`, `components/{ProductCard,ChatPanel,NavBar,Layout}.tsx`; `backend/tests/test_usability.py` (15 tests, 65 passing in all); live run through Portkey recorded in `backend/output/audit.jsonl` (alternatives in one tool call, restock filed from the chat, riddle repeated, page opened by the assistant); database rows for the seeded account (four finds, one coupon lifted to 15%, two restock requests, one marked ordered); screenshots `docs/screenshots/p9-products-filters.jpg`, `p9-hidden-friend-guest.jpg`, `p9-restock-item-page.jpg`, `p9-chat-alternatives.jpg`, `p9-coupon-three-finds.jpg`, `p9-account-collection.jpg`; `output/harness.md` section 9.

---

## Problem 10: Style the website

**Prompt I typed (own words):**

ok, Problem 10: Style the website. Add creative design so the site feels like a real campus customs storefront - fonts, colors, hierarchy, motion, product presentation, chat feel. We get points for imagination and innovation design. Write output/design.md: what changed and why it should help customers stick around and buy. Keep it concrete and short.  Well... we already did this waaaaaay before hand lol. Want to put up in broswer so i can review? Keep in mind this is a Yale campus customs site sellng apparel so we want Yale things yale school etc but with the Campus custom design wrapped by a fun halloween theme. the Yale hanuted house coulde be a famous Yale location (SOM building) and etc.. we can review and align before doing anything additional since we've already done alot

**Follow-up prompts (mid-build, in order):**

Are you able to look at a website and detect these items? https://yalebulldogblue.com/

we can at least get a "feel" then deploy our own flavor

on the test account i see "shop staff: what needs to be ordered" - in prod we should make sure this is admin only and for customer they only see their request. Right now I cannot tell which person can see it

for the costum friends we need to create 31 varients... since halloween is 10/31

in Totoro there is a Cat bus character https://en.wikipedia.org/wiki/Catbus#/media/File:Catbus_(My_Neighbor_Totoro).jpg and Totoro has little siblingshttps://ghibli.fandom.com/wiki/Smaller_Totoros?file=Mini_Totoro.jpg

So we have Labubu, Totoro, totoro siblings, cat bus, no face, soot gremlins. So 6 character styles frames, then we can apply halloween costumer varients to them to get 31. if someone finds and colects all of them then they get a voucher for free item with purchase of an item up to $100 in value only for instock items and while supplies last.

(Result: the reference site was read for feel only (white, Open Sans, flat product rows, a help bubble; computed styles and a screenshot, no copying) and then our own flavour was built: self-hosted Fraunces and Alfa Slab One, a bulldog wordmark and storefront strip, a Yale "Y" hero, a day-counter drop strip, photo category cards, residential college chips, product cards with swatches, badges, lift and stagger, a sticky item page with "Ask the bulldog about this item", the chat as a shop counter with a bulldog avatar, bubbles, typing dots and suggested questions, and Evans Hall plus Harkness Tower in the night scene. The restock queue moved to a Staff page shown only to `ADMIN_EMAILS` accounts, with the Account page stating each person's role. The Halloween set became 31 friends unlocking one per day: seven characters (Totoro, Chu Totoro, Chibi Totoro, Catbus, Labubu, Soot Sprite, No-Face) in eight costumes, with the reward ladder 3 finds = 10% coupon, 10 finds = 15%, the whole set = the free-item voucher with the stated terms.)

**Evidence:** `output/design.md`; `frontend/src/{index.css,shop.css}` (type scale, strip, wordmark, hero Y, drop strip, category cards, chips, motion), `components/{Bulldog,NavBar,ChatPanel,ProductCard,Layout}.tsx`, `pages/{Home,ProductDetail,Staff,Account}.tsx`, `halloween/HalloweenScene.tsx` (Evans Hall, Harkness Tower), `eggs/characters.tsx` (seven characters, eight costume overlays), `backend/hunt.py` (31-day set, `HUNT_DATE`, reward ladder), `backend/main.py` (hunt rate limit); 66 tests passing; `npm run build` and `npm run lint` clean; screenshots `docs/screenshots/p10-home.jpg`, `p10-products.jpg`, `p10-item.jpg`, `p10-chat.jpg`, `p10-scene.jpg`, `p10-account-tray.jpg`, `p10-staff.jpg`; `output/harness.md` section 10.

---

## Problem 11: Site testing (app check)

**Prompt I typed (own words):**

once all set and completed then we move to Problem 11 of 13: Site testing (app check). Test the live site and docuemnt it in output/app_check.html (a page we can double click to open). Include screenshots and short captions for: 1) chat checking the invetory level of an item (honest stock/price from DB), 2) the dynamic search-reuslt cards appearing after a category questions (eg: hoodie), 3) one of the usability features we added in problem 9. then make the html easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot illustrates/proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

**Follow-up prompt:** none yet.

**Evidence:** `output/app_check.html` (double-click to open; headings, screenshots and captions for the three required checks plus a bonus) with the images in `output/app_check_images/` (`inventory.jpg`, `hoodie-cards.jpg`, `sold-out-alternatives.jpg`, `filters-chips.jpg`), all taken on the live site with the real model and cross-checked against `data/campus_customs.db` by SQL; `output/harness.md` section 11.

---

## Problem 12: Audit trail, safety, finish harness

**Prompt I typed (own words):**

Problem 12 of 13: Audit trail, safety, finish harness. Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, think of some safety rules to giv the agent and put them in prompts/prompt.md. Finish output/harness.md so it is clear how the system works. Model fields in models.py and why we chose them, tools & abilities, safety rules, specs (loops,limits, result caps, models, how to run front+back)

**Follow-up prompt:** none yet.

**Evidence:** `output/audit_trail.json` (append-only JSON array of agent-loop activity: time, event, tool name, short args and results, stop reason; grown across restarts and never wiped), `backend/audit.py` (`append_json_array`, `AuditLogger.trail`), `backend/agent.py` (trail events per graph node, guard events, stop record with request and tool counts), `backend/main.py` (guard-only turns leave a stop record; root `.env` loaded), `backend/prompts/prompt.md` (section "Safety rules", nine groups; hidden-friends numbers corrected to the live ladder), `backend/tests/conftest.py` (tests write audit files to a temp folder), `backend/tests/test_chat.py` (two new tests: the array grows across runs and stays valid, a guard-only turn leaves a stop record and never the payload; 68 passing in all); `output/harness.md` section 0 (system reference: request flow, the four agent files, models and why, tools and abilities, safety by layer, specs and how to run) and section 12; live turns through Portkey after the restart filled the trail with real records.

---

## Problem 13: Push to GitHub and submit the repo URL

**Prompt I typed (own words):**

Problem 13 of 13: Push to my Github and i'll submit the Github URL

**Pasted (the assignment's final checklist):**

FINAL: push to GitHub + submit repo URL. REPO: all code in a folder named hw4; push to a PUBLIC GitHub repo; submit the repo URL on Canvas (no zip). DO NOT COMMIT (use .gitignore): .env (real keys), data/campus_customs.db, data/products/ (product images); also ignore node_modules/, __pycache__/, .venv/, frontend/dist/; include .env.example with placeholders only (e.g. PORTKEY_API_KEY=your-key-here); before pushing, run git status and confirm none of the above are staged; if any were committed earlier, remove them from history, not just the latest commit. EXPECTED FILE LAYOUT: hw4/ with AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, frontend/ (Vite React TypeScript app), backend/ (main.py run with uvicorn main:app --reload --port 8000, agent.py, models.py, tools.py, prompts/prompt.md), output/ (harness.md, design.md, usability.md, app_check.html, app_check_images/, audit_trail.json). LOCAL-ONLY DATA PACK (not in git): data/campus_customs.db and data/products/. AGENT: the agent is exactly four files under backend/: prompts/prompt.md, agent.py, tools.py, models.py. BACKEND PORT: backend on port 8000; frontend API base URL (or Vite proxy) points to http://localhost:8000. README.md: explain how to run the frontend and backend after placing the data pack, with the five steps (place the data pack at hw4/data/; copy .env.example to .env and add your API key; pip install -r requirements.txt; cd backend and uvicorn main:app --reload --port 8000; cd frontend, npm install, npm run dev). ACCEPTANCE TEST: a fresh clone contains every file above, contains no .env, no .db, no product images, and following README.md alone (plus the data pack and a key) gets the app running.

**Follow-up prompt:** none yet.

**Evidence:** public repo `https://github.com/lukepfaffyale/hw4` (single initial commit); `.gitignore` excludes `.env`, `data/` (database and product images), `node_modules/`, `__pycache__/`, `venv/` and `.venv/`, `frontend/dist/`, `backend/output/` and the working notes; `.env.example` and the pinned `requirements.txt` at the hw4 root (`backend/requirements.txt` points to it; `main.py` reads `.env` from either folder); `README.md` with the five run steps; pre-push scans for landmine markers, secret-looking strings, key values, personal data strings and em dashes, plus a reviewed `git add --dry-run`; 68 tests, build and lint green; fresh-clone check for the expected files and for the absence of `.env`, the database and product images; `output/harness.md` section 13.

---
