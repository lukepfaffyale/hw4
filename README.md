# HW4: Campus Customs shop + chatbot

A Yale merch shop for Campus Customs (a class project, not the store's real site): a React front end, a FastAPI back end, and a PydanticAI shop assistant that answers price, size and stock questions from the local database, shows the matching items on the page, and runs inside a safe agent harness.

- How the system works, start to finish: `output/harness.md` (section 0 is the reference, the rest is the build history)
- The graded write-ups: `output/usability.md`, `output/design.md`, `output/app_check.html`, `output/audit_trail.json`
- My prompts, problem by problem: `AI_prompts.md`
- Data dictionary (PII flags), data models, governance and accessibility: `docs/`

## Run it

You need Python 3.12 or newer (built on 3.14), Node 20 or newer (built on 24), the course data pack and a Portkey key.

1. **Place the data pack** at `hw4/data/` so you have `hw4/data/campus_customs.db` and `hw4/data/products/` (the product photos). Both are gitignored and never committed.
2. **Copy `.env.example` to `.env`** (same folder) and add your API key as `PORTKEY_API_KEY`. The other values can stay as they are.
3. **Install backend dependencies** (a virtual environment is recommended):

       pip install -r requirements.txt

4. **Run the backend** on port 8000:

       cd backend
       uvicorn main:app --reload --port 8000

   Health check at http://localhost:8000/health, API docs at http://localhost:8000/docs.

5. **Install and run the frontend** in a second terminal:

       cd frontend
       npm install
       npm run dev

   Open http://localhost:5173. The front end calls the back end at `http://localhost:8000` (change it with `VITE_API_URL` in `frontend/.env.local` if needed).

Windows note: create the virtual environment with `python -m venv venv` and activate it with `venv\Scripts\activate` before step 3. Drop `--reload` when something else is editing the code, so one change cannot start a second server.

## Where things are

    hw4/
      AI_prompts.md            my prompts and what each produced
      requirements.txt         pinned Python dependencies
      .env.example             placeholders only; copy to .env
      README.md
      frontend/                React + TypeScript + Vite (src/pages, src/components, src/api.ts, src/types.ts)
      backend/
        main.py                FastAPI app: products, accounts, chat, hidden friends, restock routes
        agent.py               the PydanticAI agent and the safe harness (limits, checks, audit)
        tools.py               the eight typed tools and the agent's state
        models.py              every Pydantic schema
        prompts/prompt.md      the system prompt, including the safety rules
        db.py auth.py hunt.py audit.py prompt_guard.py ratelimit.py   the web app around the agent
        data/schema.sql        the tables the app adds to the data pack
        tests/                 68 tests (pytest), run on a throwaway copy of the database
      output/
        harness.md design.md usability.md app_check.html app_check_images/ audit_trail.json
      docs/                    data dictionary, models, governance, accessibility, screenshots
      data/                    the data pack (local only)

The agent is exactly four files: `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py`, `backend/models.py`.

## The shop assistant

Open the chat ("Ask the bulldog") on any page. Every price, colour, size and stock figure it states comes from the database through its tools (or, for the item on screen, from a stock note the server reads for that turn); it never guesses. It returns the items it found as cards, narrows the Products grid to them, and can offer a page of the site (hoodies under $50, an item, your Account page). When a size is sold out it shows alternatives in that size and, for a signed-in shopper who says yes, files a restock request the shop sees on the Staff page.

Harness: PydanticAI `agent.iter` under `UsageLimits(12 requests, 20 tool calls)`, allow-listed models through Portkey (`OPENAI_MODEL`, default `gpt-5.6-luna`), a regex prompt guard on typed text, cards only from tool results, validated page links, a price check, and two append-only audit files: `output/audit_trail.json` (time, event, tool, short args and result, stop reason; committed, PII-free) and `backend/output/audit.jsonl` (every graph node; gitignored). Details in `output/harness.md` sections 0 and 12.

Endpoints: `GET /health`, `GET /products` (q, category, max_price, in_stock, sort), `GET /products/{id}`, `GET /media/products/{id}`, `POST /auth/signup`, `POST /auth/login`, `POST /auth/social`, `GET /me`, `DELETE /me`, `POST /chat`, `GET /me/activity`, `DELETE /me/activity`, `GET /hunt`, `GET /me/hunt`, `POST /me/hunt/finds`, `GET/POST /me/restock-requests`, `DELETE /me/restock-requests/{id}`, and for staff `GET /admin/restock-requests`, `GET /admin/restock-requests.csv`, `POST /admin/restock-requests/{id}/ordered`.

## Accounts

- **Seeded test user:** `test@campuscustoms.yale.edu` with the password from the course spec (PBKDF2 format, verified as shipped).
- **New accounts** are hashed with bcrypt (cost 12, per-password salt). `PASSWORD_SCHEME=pbkdf2` in `.env` writes the course format instead; login accepts both.
- **Password rules:** 12 to 64 characters, upper and lower case, a number, a symbol, no spaces, not a common password, not your name or email. The Create Account page can roll a Halloween-themed password for you.
- **Academic project:** use test passwords only, never a real one. The Account page shows everything stored about you, lets you download your chat history, cancel restock requests, and delete the account.
- **Staff:** put account emails in `ADMIN_EMAILS` (comma-separated) in `.env`; those accounts get the Staff page (`/staff`) with the restock queue and CSV export, and the server answers 403 to everyone else.
- **Social sign-in (Google, GitHub)** goes through Supabase Auth with the provider defaults. Create a Supabase project, enable the provider, add `http://localhost:5173/login` to the redirect allow-list, then put the project URL and **anon** key in `.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`) and `frontend/.env.local` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`). With the values blank the buttons are disabled.

## Checks

    cd backend && python -m pytest -q        # 68 tests: auth, chat harness, tools, usability, hygiene
    cd frontend && npm run build && npm run lint

## Hidden friends

Small friends hide around the shop in seasonal sets: Totoro, Chu Totoro, Chibi Totoro, Catbus, Labubu, a Soot Sprite and No-Face in trick-or-treat costumes. The Halloween set is 31 friends, one unlocking each day of October (`HUNT_DATE=YYYY-MM-DD` in `.env` pins the date for a demo; `HUNT_SEASON=halloween` forces the season). Each one hides on its home page until found, and each find gives the riddle for the next; the assistant repeats the current riddle if you ask. Three finds in a season earn your one coupon (10% off one item), ten finds across seasons (friend referrals count, up to three) lift it to 15%, and the whole set earns a free-item voucher: free with the purchase of another item, up to $100, in-stock items only, while supplies last. Guests can play; finds move to the account at sign-in. Add `?egg=<friend-key>` or `?spot=footer` to a page URL while testing. Class-project codes only. Write-up: `output/usability.md`.

## Look and feel

Self-hosted fonts (Fraunces for headings, Alfa Slab One for the wordmark and prices), a bulldog at the chat counter, product cards with colour swatches, size chips and badges, URL-backed filters, and a Halloween night scene of Evans Hall and Harkness Tower. The "Halloween toggle" in the nav is on by default and remembered in the browser; everything respects `prefers-reduced-motion`, nothing flashes. Design notes: `output/design.md`.
