"""Campus Customs API. Products, stock, images (Problem 3), accounts (Problem 4), the shop agent
behind POST /chat (Problem 5), and the hidden-friends collection plus restock requests (Problem 9).

Run from backend/:  uvicorn main:app --reload --port 8000
(Drop --reload when an agent is driving edits, so one change cannot spawn a second server.)
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

import agent
import auth
import db
import hunt
import prompt_guard
import tools
from audit import AuditLogger
from models import (
    ActivityItem,
    ActivityResponse,
    AdminRequester,
    AdminRestockGroup,
    AdminRestockQueue,
    AuthResponse,
    Category,
    ChatRequest,
    ChatResponse,
    DeleteActivityResponse,
    DeleteMeResponse,
    ErrorResponse,
    FindRequest,
    Health,
    HuntProgram,
    HuntProgress,
    LoginRequest,
    PasswordPolicy,
    ProductDetail,
    ProductList,
    ProductQuery,
    ProductSummary,
    RestockCreateRequest,
    RestockList,
    RestockRequest,
    RestockStatusResponse,
    SearchSort,
    SignupRequest,
    SocialLoginRequest,
    UserPublic,
)
from ratelimit import RateLimiter

# Secrets come from .env only: backend/.env first, then the hw4 root .env (the course layout keeps
# .env.example at the root). A variable set in the first file wins; neither file is ever committed.
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or ""
# Problem 9: shop staff who may see the restock queue (names and emails of who asked). Set in .env.
ADMIN_EMAILS = {e.strip().lower() for e in (os.environ.get("ADMIN_EMAILS") or "").split(",") if e.strip()}
PRODUCT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Auth brute-force limits: per client address and per email, 15-minute windows.
auth_ip_limiter = RateLimiter(limit=20, window_seconds=900)
auth_email_limiter = RateLimiter(limit=8, window_seconds=900)
# LLM endpoint: 30 chat turns per client address per 15 minutes.
chat_limiter = RateLimiter(limit=30, window_seconds=900)
# Hidden-friend finds: a daily set has 31 friends and a guest's finds are banked in one burst at
# sign-in, so this one is roomier than the auth limit while still stopping a script.
hunt_limiter = RateLimiter(limit=120, window_seconds=900)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.ensure_schema()
    yield


app = FastAPI(
    title="Campus Customs API",
    version="0.9.0",
    description="Products, stock, images, accounts, the shop agent, hidden friends and restock requests.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return field and message only. Pydantic's default echoes the submitted value, which for a
    signup would put the typed password in the response."""
    errors = [
        {"loc": [str(p) for p in e.get("loc", ())], "msg": str(e.get("msg", "")).removeprefix("Value error, ")}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


# ------------------------------------------------------------------ helpers


def _valid_product_id(product_id: str) -> str:
    if len(product_id) > 80 or not PRODUCT_ID.match(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return product_id


ALLOWED_PRODUCT_PARAMS = set(ProductQuery.model_fields)


def _query(
    request: Request,
    q: str | None = Query(default=None, max_length=80),
    category: Category | None = None,
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool = False,
    sort: SearchSort = "relevance",
) -> ProductQuery:
    # Same "extra=forbid" discipline for query strings: unknown parameters are rejected.
    unknown = set(request.query_params) - ALLOWED_PRODUCT_PARAMS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown query parameters: {sorted(unknown)}")
    return ProductQuery(q=q, category=category, max_price=max_price, in_stock=in_stock, sort=sort)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _auth_rate_limit(request: Request) -> None:
    if not auth_ip_limiter.allow(_client_key(request)):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")


def _email_rate_limit(email: str) -> None:
    if not auth_email_limiter.allow(email.lower()):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")


def _is_admin(user: db.UserRecord) -> bool:
    return user.email.lower() in ADMIN_EMAILS


def _auth_response(user: db.UserRecord) -> AuthResponse:
    token, exp = auth.make_session_token(user.id)
    return AuthResponse(
        token=token,
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        user=user.public(is_admin=_is_admin(user)),
    )


def optional_user(request: Request) -> db.UserRecord | None:
    """The signed-in shopper if a valid token was sent, else None (guest)."""
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else None
    uid = auth.read_session_token(token)
    return db.get_user_by_id(uid) if uid is not None else None


def current_user(request: Request) -> db.UserRecord:
    """Bearer-token dependency. The user id comes from the signed token, never from the client."""
    user = optional_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


def current_admin(user: db.UserRecord = Depends(current_user)) -> db.UserRecord:
    """A signed-in shopper whose email is listed in ADMIN_EMAILS. Everyone else gets 403."""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Shop staff only.")
    return user


# ------------------------------------------------------------------ health and products


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health()


@app.get("/products", response_model=ProductList)
def products(query: ProductQuery = Depends(_query)) -> ProductList:
    items, categories = db.list_products(query)
    return ProductList(items=items, total=len(items), categories=categories)


@app.get(
    "/products/{product_id}",
    response_model=ProductDetail,
    responses={404: {"model": ErrorResponse}},
)
def product(product_id: str = Depends(_valid_product_id)) -> ProductDetail:
    found = db.get_product(product_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return found


@app.get("/media/products/{product_id}", responses={404: {"model": ErrorResponse}})
def product_image(product_id: str = Depends(_valid_product_id)) -> FileResponse:
    path = db.image_path_for(product_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ------------------------------------------------------------------ accounts


@app.get("/auth/password-policy", response_model=PasswordPolicy)
def password_policy() -> PasswordPolicy:
    return PasswordPolicy()


@app.post(
    "/auth/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def signup(payload: SignupRequest, request: Request) -> AuthResponse:
    _auth_rate_limit(request)
    # Problem 9: a friend's referral code. Unknown codes are ignored rather than blocking the signup.
    referrer = db.get_user_by_referral_code(payload.referral_code) if payload.referral_code else None
    try:
        user = db.create_user(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password_hash=auth.hash_password(payload.password),
            referred_by=referrer.id if referrer else None,
        )
    except db.EmailTaken:
        raise HTTPException(status_code=409, detail="An account with that email already exists. Try signing in.")
    if referrer is not None:
        hunt.credit_referral(referrer, user)
    return _auth_response(user)


@app.post(
    "/auth/login",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(payload: LoginRequest, request: Request) -> AuthResponse:
    _auth_rate_limit(request)
    _email_rate_limit(payload.email)
    user = db.get_user_by_email(payload.email)
    if user is None:
        auth.burn_time_like_a_real_check(payload.password)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return _auth_response(user)


def _split_name(meta: dict[str, Any], email: str) -> tuple[str, str]:
    given = str(meta.get("given_name") or "").strip()
    family = str(meta.get("family_name") or "").strip()
    if given or family:
        return given or "Shopper", family or ""
    full = str(meta.get("full_name") or meta.get("name") or "").strip()
    if full:
        parts = full.split()
        return parts[0], " ".join(parts[1:])
    return email.split("@")[0][:60], ""


@app.post(
    "/auth/social",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def social_login(payload: SocialLoginRequest, request: Request) -> AuthResponse:
    """Finish a Supabase Auth OAuth sign-in (Google or GitHub, provider defaults, minimum scopes).

    The front end never sends us a provider token; it sends the Supabase access token, which we
    hand back to Supabase to confirm. We store only the provider name, the provider's user id,
    the verified email and the name. No password exists for such accounts.
    """
    _auth_rate_limit(request)
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Social sign-in is not configured on this server.")
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {payload.access_token}"},
            timeout=10.0,
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Could not reach the sign-in provider.")
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Social sign-in could not be verified.")
    info = resp.json()
    provider = str((info.get("app_metadata") or {}).get("provider") or "").lower()
    sub = str(info.get("id") or "")
    email = str(info.get("email") or "").strip().lower()
    confirmed = bool(info.get("email_confirmed_at"))
    if provider not in ("google", "github") or not sub or not email or not confirmed:
        raise HTTPException(status_code=401, detail="Social sign-in did not return a verified email.")

    user = db.get_user_by_provider(provider, sub)
    if user is None:
        existing = db.get_user_by_email(email)
        if existing is not None:
            # Provider-verified email matches an existing account: link it, keep its data.
            db.link_social(existing.id, provider, sub)
            user = db.get_user_by_id(existing.id)
        else:
            first, last = _split_name(info.get("user_metadata") or {}, email)
            user = db.create_user(
                first_name=first,
                last_name=last or "",
                email=email,
                password_hash=auth.UNUSABLE_PASSWORD,
                auth_provider=provider,
                provider_user_id=sub,
            )
    assert user is not None
    return _auth_response(user)


@app.get("/me", response_model=UserPublic, responses={401: {"model": ErrorResponse}})
def me(user: db.UserRecord = Depends(current_user)) -> UserPublic:
    return user.public(is_admin=_is_admin(user))


@app.delete("/me", response_model=DeleteMeResponse, responses={401: {"model": ErrorResponse}})
def delete_me(user: db.UserRecord = Depends(current_user)) -> DeleteMeResponse:
    """Delete the signed-in shopper's chat history, finds, coupon, rewards, restock requests and
    account. Their own rows only."""
    removed = db.delete_user(user.id)
    return DeleteMeResponse(ok=True, deleted_messages=removed)


# ------------------------------------------------------------------ chat (the agent)

HISTORY_TURNS = 20
GUARD_ONLY_REPLY = (
    "I can only help with Campus Customs gear, so I set that message aside. "
    "Ask me about hoodies, crews, tees, sizes or prices."
)


def _products_json(cards: list[ProductSummary]) -> str:
    return json.dumps([c.model_dump() for c in cards])


def _parse_products(raw: str | None) -> list[ProductSummary]:
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: list[ProductSummary] = []
    for item in items if isinstance(items, list) else []:
        try:
            out.append(ProductSummary.model_validate(item))
        except Exception:  # noqa: BLE001  (older rows from the data pack have a different shape)
            continue
    return out


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={429: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def chat(
    payload: ChatRequest, request: Request, user: db.UserRecord | None = Depends(optional_user)
) -> ChatResponse:
    """One turn with the shop agent. Signed-in shoppers get server-side memory and their turns are
    stored (cleaned text only); guests send their own recent turns back and nothing is stored."""
    if not chat_limiter.allow(_client_key(request)):
        raise HTTPException(status_code=429, detail="Slow down a little; try again in a few minutes.")

    # Prompt guard on the typed channel: flagged blocks are dropped and recorded without the payload.
    cleaned, flags = prompt_guard.strip_injections(payload.message, source="chat", channel="typed")
    prompt_guard.append_flags(flags)
    cleaned = cleaned.replace("[INJECTION_DROPPED]", "").strip()
    flagged = bool(flags)

    # Page context (Problem 8): the browser says where it is; the product itself is re-read from
    # the database so the agent works from our facts, never from a name the browser sent.
    page_product = None
    if payload.page and payload.page.product_id:
        page_product = db.get_product(payload.page.product_id)

    # Identity (Problem 8) comes from the verified session, never from chat text.
    state = tools.ChatState(
        signed_in=user is not None,
        user_id=user.id if user else None,
        shopper_first_name=user.first_name if user else None,
        shopper_last_name=user.last_name if user else None,
        shopper_email=user.email if user else None,
        page_route=payload.page.route if payload.page else None,
        page_product=page_product,
    )
    if page_product is not None:
        state.seen[page_product.product_id] = page_product  # verified against the database above
    deps = tools.ChatDeps(state=state, audit=AuditLogger(run_id=secrets.token_hex(6)))
    deps.audit.log(
        "context",
        extra={
            "signed_in": state.signed_in,
            "page_route": state.page_route,
            "page_product": page_product.product_id if page_product else None,
            "tools": list(state.tool_names),
        },
    )

    if flagged:
        # The trail records that the guard fired and how many blocks it dropped, never the payload.
        deps.audit.trail("guard", check="prompt_guard", result=f"{len(flags)} injection block(s) dropped before the model")
    if not cleaned:
        deps.audit.log("guardrail", thought="message fully dropped by prompt guard")
        deps.audit.trail("stop", stop_reason="guardrail", requests=0, tool_calls=0, ms=0)
        return ChatResponse(reply=GUARD_ONLY_REPLY, products=[], stopped_reason="guardrail", flagged=True, signed_in=user is not None)

    if user is not None:
        turns = [(r.role, r.content) for r in db.list_chat_messages(user.id, HISTORY_TURNS)]
    else:
        turns = [(t.role, t.content) for t in payload.history]
    history = agent.history_from_turns(turns)

    try:
        outcome = await agent.run_chat(cleaned, deps=deps, history=history)
    except RuntimeError as exc:  # missing key or disallowed model: configuration, not the shopper
        raise HTTPException(status_code=503, detail=str(exc))

    cards = [state.seen[pid] for pid in outcome.product_ids if pid in state.seen]

    if user is not None:
        db.add_chat_message(user.id, "user", cleaned, None)
        db.add_chat_message(user.id, "assistant", outcome.reply, _products_json(cards))

    return ChatResponse(
        reply=outcome.reply,
        products=cards,
        stopped_reason=outcome.stopped_reason,
        flagged=flagged,
        signed_in=user is not None,
        go_to=outcome.go_to,
    )


@app.get("/me/activity", response_model=ActivityResponse, responses={401: {"model": ErrorResponse}})
def my_activity(user: db.UserRecord = Depends(current_user)) -> ActivityResponse:
    """The shopper's own chat turns, oldest first, with the cards that were shown."""
    rows = db.list_chat_messages(user.id, limit=200)
    items = [
        ActivityItem(id=r.id, role=r.role, content=r.content, products=_parse_products(r.products_json), created_at=r.created_at)  # type: ignore[arg-type]
        for r in rows
    ]
    return ActivityResponse(items=items, total=len(items))


@app.delete("/me/activity", response_model=DeleteActivityResponse, responses={401: {"model": ErrorResponse}})
def delete_my_activity(user: db.UserRecord = Depends(current_user)) -> DeleteActivityResponse:
    return DeleteActivityResponse(ok=True, deleted=db.delete_chat_messages(user.id))


# ------------------------------------------------------------------ hidden friends (Problem 4 egg, Problem 9 collection)


@app.get("/hunt", response_model=HuntProgram)
def hunt_program() -> HuntProgram:
    """What can be found this season and what it earns. Public, no PII, so guests can play too."""
    return hunt.program()


@app.get("/me/hunt", response_model=HuntProgress, responses={401: {"model": ErrorResponse}})
def my_hunt(user: db.UserRecord = Depends(current_user)) -> HuntProgress:
    return hunt.progress(user)


@app.post(
    "/me/hunt/finds",
    response_model=HuntProgress,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def record_find(payload: FindRequest, request: Request, user: db.UserRecord = Depends(current_user)) -> HuntProgress:
    """The shopper tapped a hidden friend. The server decides what that earns: a repeat find
    changes nothing, three finds earn the coupon, the full set lifts it, ten finds earn the free
    item. Codes are issued here and nowhere else."""
    if not hunt_limiter.allow(_client_key(request)):
        raise HTTPException(status_code=429, detail="That is a lot of finds at once. Try again in a few minutes.")
    result = hunt.record_find(user, payload.season, payload.character)
    if result is None:
        raise HTTPException(status_code=404, detail="That friend is not hiding this season.")
    return result


# ------------------------------------------------------------------ restock requests (Problem 9)


def _restock_model(row: db.RestockRow) -> RestockRequest:
    return RestockRequest(
        id=row.id,
        product_id=row.product_id,
        product_name=row.product_name,
        size=row.size,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@app.get("/me/restock-requests", response_model=RestockList, responses={401: {"model": ErrorResponse}})
def my_restock_requests(user: db.UserRecord = Depends(current_user)) -> RestockList:
    rows = db.list_restock_requests(user.id)
    return RestockList(items=[_restock_model(r) for r in rows], total=len(rows))


@app.post(
    "/me/restock-requests",
    response_model=RestockStatusResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_restock_request(
    payload: RestockCreateRequest, request: Request, user: db.UserRecord = Depends(current_user)
) -> RestockStatusResponse:
    """The item page's "Request a restock" button. Same rule as the agent's tool: only a size the
    database says is at zero, one open request per product and size, ten open at most."""
    _auth_rate_limit(request)
    result = tools.create_restock(user.id, payload.product_id, payload.size)
    if not result.ok or result.request_id is None:
        raise HTTPException(status_code=409, detail=result.error or "Could not open that request.")
    row = db.get_restock_request(result.request_id)
    assert row is not None
    return RestockStatusResponse(ok=True, request=_restock_model(row))


@app.delete(
    "/me/restock-requests/{request_id}",
    response_model=RestockStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def cancel_restock_request(request_id: int, user: db.UserRecord = Depends(current_user)) -> RestockStatusResponse:
    row = db.cancel_restock_request(user.id, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No such request on your account.")
    return RestockStatusResponse(ok=True, request=_restock_model(row))


def _queue() -> AdminRestockQueue:
    groups: dict[tuple[str, str], AdminRestockGroup] = {}
    for r in db.open_restock_queue():
        g = groups.get((r.product_id, r.size))
        if g is None:
            g = AdminRestockGroup(product_id=r.product_id, product_name=r.product_name, size=r.size, open_count=0, requested_by=[])  # type: ignore[arg-type]
            groups[(r.product_id, r.size)] = g
        g.open_count += 1
        g.requested_by.append(AdminRequester(request_id=r.id, name=r.user_name, email=r.user_email, created_at=r.created_at))
    ordered = sorted(groups.values(), key=lambda g: (-g.open_count, g.product_name, g.size))
    return AdminRestockQueue(
        groups=ordered,
        total_open=sum(g.open_count for g in ordered),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )


@app.get(
    "/admin/restock-requests",
    response_model=AdminRestockQueue,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_restock_queue(_: db.UserRecord = Depends(current_admin)) -> AdminRestockQueue:
    """What needs ordering, most-requested first, with who asked (shop staff only)."""
    return _queue()


@app.get(
    "/admin/restock-requests.csv",
    response_class=PlainTextResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def admin_restock_csv(_: db.UserRecord = Depends(current_admin)) -> PlainTextResponse:
    """The same queue as a CSV for the ordering spreadsheet."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["product_id", "product_name", "size", "open_requests", "request_id", "requested_by", "email", "requested_at"])
    for g in _queue().groups:
        for who in g.requested_by:
            writer.writerow([g.product_id, g.product_name, g.size, g.open_count, who.request_id, who.name, who.email, who.created_at])
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="restock-requests.csv"'},
    )


@app.post(
    "/admin/restock-requests/{request_id}/ordered",
    response_model=RestockStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def admin_mark_ordered(request_id: int, _: db.UserRecord = Depends(current_admin)) -> RestockStatusResponse:
    row = db.mark_restock_ordered(request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No such request.")
    return RestockStatusResponse(ok=True, request=_restock_model(row))
