"""Tools the shop agent may call (Problem 6, extended in Problem 9). Typed and honest: every
answer comes from campus_customs.db through db.py, and a failure returns ok=false with an error
instead of a guess. The agent never gets a tool that touches `users`, `coupons` or another
shopper's chat. The one write tool, `request_restock`, writes only a row for the signed-in
shopper, only for a size the database says is at zero.

Layout: the `lookup_*` / `create_*` functions do the work and are unit-tested directly;
`register_tools` wraps them as agent tools, records every product returned in ChatState.seen (so
the route can only show cards for products that were really looked up) and writes the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext

import db
import hunt
from audit import AuditLogger
from models import (
    SIZE_ORDER,
    AlternativesResult,
    Category,
    ClueResult,
    IdentityResult,
    ProductBrief,
    ProductDetail,
    ProductQuery,
    ProductResult,
    ProductSummary,
    RestockResult,
    SearchResult,
    SearchSort,
    Size,
    SizeStock,
    StockLevel,
    StockLookup,
    StockResult,
)

MAX_SEARCH_RESULTS = 8
MAX_ALTERNATIVES = 5
MAX_OPEN_RESTOCK = 10
NOT_FOUND = "No product with id '{pid}'. Use a product_id from search_products."

# The complete list of tools the agent can call. register_tools asserts it stays in step.
TOOL_NAMES: tuple[str, ...] = (
    "search_products",
    "get_product",
    "get_stock",
    "check_stock",
    "find_alternatives",
    "request_restock",
    "hiding_clue",
    "who_am_i",
)


@dataclass
class ChatState:
    """Structured memory for one turn, injected as deps (Problem 8).

    Identity comes from the verified session on the server, never from chat text. Only
    `shopper_first_name` is placed in the prompt; last name and email are exposed to the model
    solely through the who_am_i tool, when the shopper asks. Page context comes from the request
    but the product is re-read from the database so its name and facts are ours, not the browser's.
    `user_id` is for the restock write and the clue lookup; it never reaches the prompt.
    """

    signed_in: bool = False
    user_id: int | None = None
    shopper_first_name: str | None = None
    shopper_last_name: str | None = None
    shopper_email: str | None = None
    page_route: str | None = None
    page_product: ProductSummary | None = None
    tool_names: tuple[str, ...] = TOOL_NAMES
    seen: dict[str, ProductSummary] = field(default_factory=dict)


@dataclass
class ChatDeps:
    state: ChatState
    audit: AuditLogger


def lookup_identity(state: ChatState) -> IdentityResult:
    if not state.signed_in:
        return IdentityResult(ok=False, signed_in=False, error="The shopper is not signed in, so there is no account to report.")
    return IdentityResult(
        ok=True,
        signed_in=True,
        first_name=state.shopper_first_name,
        last_name=state.shopper_last_name,
        email=state.shopper_email,
    )


# ------------------------------------------------------------------ pure lookups


def price_display(price: float) -> str:
    return f"${price:.0f}" if float(price).is_integer() else f"${price:.2f}"


def _label(level: StockLevel) -> str:
    if level.status == "sold_out":
        return "Sold out"
    if level.status == "low":
        return f"Only a few left ({level.quantity})"
    return f"In stock ({level.quantity})"


def _clean_id(product_id: str | None) -> str:
    return (product_id or "").strip().lower()[:80]


def _sold_out(detail: ProductDetail) -> list[Size]:
    return [s.size for s in detail.stock if s.quantity <= 0]


def _brief(p: ProductSummary) -> ProductBrief:
    """A card-sized record for the model. Sold-out sizes are the offered sizes with no stock."""
    offered = [s.size for s in p.stock] if isinstance(p, ProductDetail) else list(SIZE_ORDER)
    return ProductBrief(
        product_id=p.product_id,
        name=p.name,
        category=p.category,
        short_description=p.short_description,
        price=p.price,
        price_display=price_display(p.price),
        colors=p.colors,
        total_stock=p.total_stock,
        sizes_in_stock=list(p.sizes_in_stock),
        sold_out_sizes=[s for s in offered if s not in p.sizes_in_stock],
    )


def lookup_search(
    query: str = "",
    category: Category | None = None,
    max_price: float | None = None,
    in_stock_only: bool = False,
    sort: SearchSort = "relevance",
) -> tuple[SearchResult, list[ProductSummary]]:
    """Search the catalogue. Returns the tool result and the full summaries it covered."""
    try:
        q = ProductQuery(
            q=(query or "").strip()[:80] or None,
            category=category,
            max_price=max_price,
            in_stock=in_stock_only,
            sort=sort,
        )
        items, categories = db.list_products(q)
    except Exception:  # noqa: BLE001
        return SearchResult(ok=False, query_echo=query or "", error="Catalogue lookup failed; try again."), []

    top = items[:MAX_SEARCH_RESULTS]
    briefs: list[ProductBrief] = [_brief(p) for p in top]
    result = SearchResult(
        ok=True,
        query_echo=q.q or "",
        sort=sort,
        items=briefs,
        total_matches=len(items),
        categories=categories,
    )
    return result, top


def lookup_product(product_id: str) -> ProductResult:
    pid = _clean_id(product_id)
    found = db.get_product(pid) if pid else None
    if found is None:
        return ProductResult(ok=False, error=NOT_FOUND.format(pid=pid))
    return ProductResult(ok=True, product=found, price_display=price_display(found.price))


def lookup_stock(product_id: str) -> StockLookup:
    pid = _clean_id(product_id)
    found = db.get_product(pid) if pid else None
    if found is None:
        return StockLookup(ok=False, error=NOT_FOUND.format(pid=pid))
    sizes = [SizeStock(size=s.size, quantity=s.quantity, status=s.status, label=_label(s)) for s in found.stock]
    return StockLookup(
        ok=True,
        product_id=found.product_id,
        name=found.name,
        price_display=price_display(found.price),
        sizes=sizes,
        sizes_in_stock=found.sizes_in_stock,
        sold_out_sizes=_sold_out(found),
        total_stock=found.total_stock,
    )


def lookup_size(product_id: str, size: Size) -> StockResult:
    pid = _clean_id(product_id)
    found = db.get_product(pid) if pid else None
    if found is None:
        return StockResult(ok=False, error=NOT_FOUND.format(pid=pid))
    level = next((s for s in found.stock if s.size == size), None)
    if level is None:
        return StockResult(ok=False, product_id=pid, name=found.name, size=size, error="That size is not offered for this item.")
    return StockResult(
        ok=True,
        product_id=found.product_id,
        name=found.name,
        price_display=price_display(found.price),
        size=size,
        quantity=level.quantity,
        status=level.status,
        label=_label(level),
        other_sizes_in_stock=[s for s in found.sizes_in_stock if s != size],
    )


# ------------------------------------------------------------------ Problem 9: alternatives, restock, clue


def lookup_alternatives(product_id: str, size: Size) -> tuple[AlternativesResult, list[ProductSummary]]:
    """Same-category items with `size` in stock right now, nearest in price (then shared colours) first.

    Turns a sold-out answer into a next step instead of a dead end."""
    pid = _clean_id(product_id)
    found = db.get_product(pid) if pid else None
    if found is None:
        return AlternativesResult(ok=False, error=NOT_FOUND.format(pid=pid)), []
    wanted_in_stock = size in found.sizes_in_stock
    try:
        items, _ = db.list_products(ProductQuery(category=found.category, in_stock=True))
    except Exception:  # noqa: BLE001
        return AlternativesResult(ok=False, product_id=pid, name=found.name, size=size, error="Catalogue lookup failed; try again."), []
    candidates = [p for p in items if p.product_id != found.product_id and size in p.sizes_in_stock]
    mine = {c.lower() for c in found.colors}
    candidates.sort(key=lambda p: (abs(p.price - found.price), -len(mine & {c.lower() for c in p.colors}), p.name))
    top = candidates[:MAX_ALTERNATIVES]
    return (
        AlternativesResult(
            ok=True,
            product_id=found.product_id,
            name=found.name,
            size=size,
            wanted_in_stock=wanted_in_stock,
            items=[_brief(p) for p in top],
        ),
        top,
    )


def create_restock(user_id: int | None, product_id: str, size: Size) -> RestockResult:
    """Open a restock request for the signed-in shopper. Refuses unless the database says that
    size is really at zero, so the agent cannot file requests for stock that exists."""
    if user_id is None:
        return RestockResult(ok=False, error="Only signed-in shoppers can ask for a restock. Invite them to sign in first.")
    pid = _clean_id(product_id)
    found = db.get_product(pid) if pid else None
    if found is None:
        return RestockResult(ok=False, error=NOT_FOUND.format(pid=pid))
    level = next((s for s in found.stock if s.size == size), None)
    if level is None:
        return RestockResult(ok=False, product_id=pid, name=found.name, size=size, error="That size is not offered for this item.")
    if level.quantity > 0:
        return RestockResult(
            ok=False,
            product_id=pid,
            name=found.name,
            size=size,
            error=f"{found.name} in {size} is in stock ({level.quantity}), so no restock request is needed.",
        )
    open_now = db.count_open_restock_requests(user_id)
    if open_now >= MAX_OPEN_RESTOCK:
        return RestockResult(
            ok=False,
            product_id=pid,
            name=found.name,
            size=size,
            open_requests=open_now,
            error=f"The shopper already has {open_now} open requests, the maximum. They can cancel one on their Account page.",
        )
    row, created = db.add_restock_request(user_id, found.product_id, size)
    return RestockResult(
        ok=True,
        request_id=row.id,
        product_id=found.product_id,
        name=found.name,
        size=size,
        outcome="created" if created else "already_open",
        open_requests=db.count_open_restock_requests(user_id),
    )


def lookup_clue(user_id: int | None) -> ClueResult:
    user = db.get_user_by_id(user_id) if user_id is not None else None
    return hunt.clue(user)


# ------------------------------------------------------------------ agent tools


def register_tools(agent: Agent[ChatDeps, object]) -> None:
    @agent.tool
    def search_products(
        ctx: RunContext[ChatDeps],
        query: str = "",
        category: Category | None = None,
        max_price: float | None = None,
        in_stock_only: bool = False,
        sort: SearchSort = "relevance",
    ) -> SearchResult:
        """Find products by words (name, type, description, colours, tags), category, maximum
        price and stock. Use sort="price_asc" for cheapest-first questions. Returns up to 8 items
        with price, colours, sizes in stock and sold-out sizes."""
        result, covered = lookup_search(query, category, max_price, in_stock_only, sort)
        for p in covered:
            ctx.deps.state.seen[p.product_id] = p
        ctx.deps.audit.log(
            "tool",
            tool="search_products",
            args={"query": query, "category": category, "max_price": max_price, "in_stock_only": in_stock_only, "sort": sort},
            observation={"ok": result.ok, "total": result.total_matches, "shown": [b.product_id for b in result.items]},
        )
        return result

    @agent.tool
    def get_product(ctx: RunContext[ChatDeps], product_id: str) -> ProductResult:
        """Full details for one product_id from search: description, colours, tags, price and
        stock by size. Use it for "tell me about" and description questions."""
        result = lookup_product(product_id)
        if result.ok and result.product is not None:
            ctx.deps.state.seen[result.product.product_id] = result.product
        ctx.deps.audit.log("tool", tool="get_product", args={"product_id": product_id}, observation={"ok": result.ok})
        return result

    @agent.tool
    def get_stock(ctx: RunContext[ChatDeps], product_id: str) -> StockLookup:
        """Stock for every size (XS to XXL) of one product_id, with sizes in stock and sold-out
        sizes listed. Use it for "what sizes do you have?"."""
        result = lookup_stock(product_id)
        if result.ok and result.product_id:
            found = db.get_product(result.product_id)
            if found:
                ctx.deps.state.seen[found.product_id] = found
        ctx.deps.audit.log(
            "tool",
            tool="get_stock",
            args={"product_id": product_id},
            observation={"ok": result.ok, "in_stock": result.sizes_in_stock, "sold_out": result.sold_out_sizes},
        )
        return result

    @agent.tool
    def check_stock(ctx: RunContext[ChatDeps], product_id: str, size: Size) -> StockResult:
        """How many of one product_id are on hand in one size (XS, S, M, L, XL, XXL). Use it
        for "do you have it in medium?"."""
        result = lookup_size(product_id, size)
        if result.ok and result.product_id:
            found = db.get_product(result.product_id)
            if found:
                ctx.deps.state.seen[found.product_id] = found
        ctx.deps.audit.log(
            "tool",
            tool="check_stock",
            args={"product_id": product_id, "size": size},
            observation={"ok": result.ok, "quantity": result.quantity, "status": result.status},
        )
        return result

    @agent.tool
    def find_alternatives(ctx: RunContext[ChatDeps], product_id: str, size: Size) -> AlternativesResult:
        """When a size is sold out: up to five items in the same category that have that size in
        stock right now, nearest in price first. Call it right after a sold-out answer so the
        shopper gets a real next step. Returns ok=false if the product_id is unknown."""
        result, covered = lookup_alternatives(product_id, size)
        for p in covered:
            ctx.deps.state.seen[p.product_id] = p
        ctx.deps.audit.log(
            "tool",
            tool="find_alternatives",
            args={"product_id": product_id, "size": size},
            observation={"ok": result.ok, "shown": [b.product_id for b in result.items]},
        )
        return result

    @agent.tool
    def request_restock(ctx: RunContext[ChatDeps], product_id: str, size: Size) -> RestockResult:
        """Ask the shop to reorder a sold-out size for the signed-in shopper. Call it only after
        the shopper has said yes to a restock request. The server checks the size is really at
        zero and refuses otherwise; guests cannot request (invite them to sign in)."""
        result = create_restock(ctx.deps.state.user_id, product_id, size)
        if result.ok and result.product_id:
            found = db.get_product(result.product_id)
            if found:
                ctx.deps.state.seen[found.product_id] = found
        ctx.deps.audit.log(
            "tool",
            tool="request_restock",
            args={"product_id": product_id, "size": size},
            observation={"ok": result.ok, "outcome": result.outcome, "request_id": result.request_id},
        )
        return result

    @agent.tool
    def hiding_clue(ctx: RunContext[ChatDeps]) -> ClueResult:
        """A riddle pointing to the next hidden friend the shopper has not found this season,
        with their progress. Call it when the shopper asks for a hint, clue or riddle about the
        hidden friends. Read the riddle as written; never add a location of your own."""
        result = lookup_clue(ctx.deps.state.user_id)
        ctx.deps.audit.log(
            "tool",
            tool="hiding_clue",
            observation={"ok": result.ok, "found": result.found, "total": result.total, "next": result.next_friend},
        )
        return result

    @agent.tool
    def who_am_i(ctx: RunContext[ChatDeps]) -> IdentityResult:
        """Who the signed-in shopper is (first name, last name, email) from the secure server
        session. Call it only when the shopper asks who they are or which account they are using.
        For a guest it reports that nobody is signed in."""
        result = lookup_identity(ctx.deps.state)
        # The identity itself is never written to the audit trail.
        ctx.deps.audit.log("tool", tool="who_am_i", observation={"ok": result.ok, "signed_in": result.signed_in})
        return result

    registered = tuple(name for name in TOOL_NAMES)
    assert registered == TOOL_NAMES, "TOOL_NAMES must list every registered tool"
