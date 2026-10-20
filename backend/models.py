"""Pydantic schemas: the typed contract between the database, the API and the front end.

Every response the API sends is one of these models. Request bodies use `extra="forbid"` so
unknown fields are rejected. Passwords never appear in any response model.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from auth import PASSWORD_MAX, PASSWORD_MIN, password_issues

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ORDER: tuple[Size, ...] = ("XS", "S", "M", "L", "XL", "XXL")

Category = Literal[
    "hoodie",
    "crewneck",
    "t-shirt",
    "quarter-zip",
    "jacket",
    "performance",
    "other",
]

AuthProvider = Literal["password", "google", "github"]
SearchSort = Literal["relevance", "price_asc", "price_desc", "name"]


class Health(BaseModel):
    ok: bool = True


# ------------------------------------------------------------------ products


class StockLevel(BaseModel):
    """One row of `inventory`: how many of a product are on hand in one size."""

    size: Size
    quantity: int = Field(ge=0)
    status: Literal["in_stock", "low", "sold_out"]


class ProductSummary(BaseModel):
    """A `catalogue` row shaped for a product card, plus which sizes are in stock (Problem 9) so a
    shopper can see their size on the card without opening the item."""

    product_id: str
    name: str
    garment_type: str
    category: Category
    short_description: str
    colors: list[str]
    price: float = Field(ge=0)
    image_url: str
    total_stock: int = Field(ge=0)
    sizes_in_stock: list[Size] = Field(default_factory=list)


class ProductDetail(ProductSummary):
    """Everything on the single-item page: full text, tags and stock by size."""

    description: str
    search_tags: list[str]
    stock: list[StockLevel]


class ProductList(BaseModel):
    items: list[ProductSummary]
    total: int = Field(ge=0)
    categories: list[Category]


class ProductQuery(BaseModel):
    """Query parameters accepted by GET /products. Unknown params are rejected."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(default=None, max_length=80)
    category: Category | None = None
    max_price: float | None = Field(default=None, ge=0)
    in_stock: bool = False
    sort: SearchSort = "relevance"


class ErrorResponse(BaseModel):
    detail: str


# ------------------------------------------------------------------ auth

_NAME_OK = re.compile(r"^[^\x00-\x1f\x7f<>]{1,60}$")


def _clean_name(value: str) -> str:
    v = " ".join(value.split())
    if not v or not _NAME_OK.match(v):
        raise ValueError("must be 1 to 60 characters with no control characters or angle brackets")
    return v


class SignupRequest(BaseModel):
    """Create-account payload. Strict password policy enforced here, mirrored in the front end."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    confirm_password: str = Field(min_length=1, max_length=PASSWORD_MAX)
    # Problem 9: optional friend-referral code (another shopper's code, printed on their Account page).
    referral_code: str | None = Field(default=None, max_length=16)

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("referral_code")
    @classmethod
    def _referral(cls, v: str | None) -> str | None:
        code = (v or "").strip().upper().replace("-", "")
        if not code:
            return None
        if not re.fullmatch(r"[A-Z0-9]{6,12}", code):
            raise ValueError("Referral code should be 6 to 12 letters and numbers")
        return code

    @model_validator(mode="after")
    def _password_rules(self) -> "SignupRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        issues = password_issues(
            self.password, email=self.email, first_name=self.first_name, last_name=self.last_name
        )
        if issues:
            raise ValueError("Password needs: " + "; ".join(issues))
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.strip().lower()


class SocialLoginRequest(BaseModel):
    """The access token Supabase Auth issued after the provider's own sign-in."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(min_length=20, max_length=4096)


class UserPublic(BaseModel):
    """What the front end may know about the signed-in shopper. Never includes the hash."""

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    auth_provider: AuthProvider
    created_at: str
    is_admin: bool = False  # Problem 9: listed in ADMIN_EMAILS; unlocks the restock queue


class AuthResponse(BaseModel):
    token: str
    expires_at: str
    user: UserPublic


class DeleteMeResponse(BaseModel):
    ok: bool = True
    deleted_messages: int = Field(ge=0)


# ------------------------------------------------------------------ chat (Problem 5)


class ChatTurn(BaseModel):
    """One prior turn a guest's browser sends back (signed-in shoppers use server-side history)."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message (Problem 8).

    The product name is resolved from the database by the server; a name sent by the browser is
    accepted only as a hint and never quoted as a fact."""

    model_config = ConfigDict(extra="forbid")

    route: str = Field(max_length=200, pattern=r"^/[A-Za-z0-9/_\-.]*$")
    product_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    product_name: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)
    page: PageContext | None = None


class IdentityResult(BaseModel):
    """What the who_am_i tool returns: the signed-in shopper from the server session."""

    ok: bool
    signed_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    error: str | None = None


class PageLink(BaseModel):
    """A page on this site the agent wants to send the shopper to (Problem 9). The harness
    validates the route against the site's own pages before the browser ever sees it."""

    route: str = Field(max_length=300, description="Site route such as /products?category=hoodie&max_price=50 or /products/<product_id>.")
    label: str = Field(max_length=80, description="Button text, e.g. 'See hoodies under $50'.")
    navigate: bool = Field(default=False, description="True only when the shopper asked to be taken there.")


class ChatReply(BaseModel):
    """The agent's structured output. product_ids may only name products seen in tool results."""

    reply: str = Field(max_length=1500, description="Your message to the shopper.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Product ids from tool results to show as cards, most relevant first.",
    )
    go_to: PageLink | None = Field(
        default=None,
        description="Optional page on this site to offer (or open, if navigate is true). Leave null unless a page helps.",
    )


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductSummary]
    stopped_reason: str
    flagged: bool
    signed_in: bool
    go_to: PageLink | None = None


# Tool results (Problem 6): typed, and never a guess. Every result has `ok`; ok=false carries an
# `error` the agent can repeat to the shopper instead of made-up data. Field choices are explained
# in output/harness.md section 6.

StockStatus = Literal["in_stock", "low", "sold_out"]


class ProductBrief(BaseModel):
    """One search hit: enough to answer price, colour and availability without a second call."""

    product_id: str
    name: str
    category: Category
    short_description: str
    price: float
    price_display: str
    colors: list[str]
    total_stock: int
    sizes_in_stock: list[Size]
    sold_out_sizes: list[Size]


class SearchResult(BaseModel):
    ok: bool
    query_echo: str = ""
    sort: SearchSort = "relevance"
    items: list[ProductBrief] = Field(default_factory=list)
    total_matches: int = 0
    categories: list[Category] = Field(default_factory=list)
    error: str | None = None


class ProductResult(BaseModel):
    """Full product record for description questions; includes stock by size."""

    ok: bool
    product: ProductDetail | None = None
    price_display: str | None = None
    error: str | None = None


class SizeStock(BaseModel):
    size: Size
    quantity: int = Field(ge=0)
    status: StockStatus
    label: str  # "In stock (12)", "Only a few left (2)", "Sold out"


class StockLookup(BaseModel):
    """Stock by size for one product: the answer to "what sizes do you have?"."""

    ok: bool
    product_id: str | None = None
    name: str | None = None
    price_display: str | None = None
    sizes: list[SizeStock] = Field(default_factory=list)
    sizes_in_stock: list[Size] = Field(default_factory=list)
    sold_out_sizes: list[Size] = Field(default_factory=list)
    total_stock: int = 0
    error: str | None = None


class StockResult(BaseModel):
    """One size of one product: the answer to "do you have it in medium?"."""

    ok: bool
    product_id: str | None = None
    name: str | None = None
    price_display: str | None = None
    size: Size | None = None
    quantity: int | None = None
    status: StockStatus | None = None
    label: str | None = None
    other_sizes_in_stock: list[Size] = Field(default_factory=list)
    error: str | None = None


# Problem 9 tool results


class AlternativesResult(BaseModel):
    """Same-category items that have the wanted size in stock right now, nearest in price first."""

    ok: bool
    product_id: str | None = None
    name: str | None = None
    size: Size | None = None
    wanted_in_stock: bool | None = None  # True means the original item has that size after all
    items: list[ProductBrief] = Field(default_factory=list)
    error: str | None = None


RestockStatus = Literal["open", "ordered", "cancelled"]


class RestockResult(BaseModel):
    """Outcome of asking the shop to reorder a sold-out size for the signed-in shopper."""

    ok: bool
    request_id: int | None = None
    product_id: str | None = None
    name: str | None = None
    size: Size | None = None
    outcome: Literal["created", "already_open"] | None = None
    open_requests: int | None = None
    error: str | None = None


class ClueResult(BaseModel):
    """A riddle for the next hidden friend the shopper has not found this season."""

    ok: bool
    signed_in: bool
    season_name: str | None = None
    found: int = 0
    total: int = 0
    next_friend: str | None = None
    riddle: str | None = None
    note: str | None = None
    error: str | None = None


class ActivityItem(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductSummary] = Field(default_factory=list)
    created_at: str


class ActivityResponse(BaseModel):
    items: list[ActivityItem]
    total: int = Field(ge=0)


class DeleteActivityResponse(BaseModel):
    ok: bool = True
    deleted: int = Field(ge=0)


# ------------------------------------------------------------------ hidden friends (Problem 4 egg, Problem 9 collection)

FRIEND_KEY = r"^[a-z]+(?:-[a-z]+)*$"


class Coupon(BaseModel):
    """The shopper's single coupon: one per account, good for one item, once. Earned by finding
    three friends in a season (10%); completing the season's set lifts it to 15%."""

    code: str
    discount_pct: int = Field(ge=0, le=100)
    scope: Literal["one_item"]
    found_character: str
    created_at: str
    redeemed_at: str | None
    already_claimed: bool


FREE_ITEM_TERMS = (
    "Free item with the purchase of another item, up to $100 in value, in-stock items only, while supplies last. "
    "Class-project voucher, not redeemable at the real store."
)


class Reward(BaseModel):
    """The big one: a free-item voucher for finding a whole seasonal set."""

    kind: Literal["free_item"]
    code: str
    max_value_usd: int = Field(ge=0)
    terms: str = FREE_ITEM_TERMS
    created_at: str
    redeemed_at: str | None


class HuntFriend(BaseModel):
    key: str
    name: str
    home_route: str  # the page where this friend always appears until found; "/products/*" = any item page
    riddle: str
    day: int | None = None  # daily sets: the day of the month this friend unlocks
    available: bool = True  # can it be found today?
    available_from: str  # MM-DD


class HuntSeason(BaseModel):
    key: str
    name: str
    starts: str  # MM-DD
    ends: str  # MM-DD
    status: Literal["active", "coming", "past"]
    daily: bool = False
    today: str  # MM-DD, the programme's idea of today (HUNT_DATE can pin it)
    available_count: int = Field(ge=0)
    friends: list[HuntFriend]


class HuntMilestones(BaseModel):
    coupon_at: int  # finds in a season that earn the coupon
    coupon_pct: int
    lift_at: int  # finds across seasons (referrals count) that lift the coupon
    lift_pct: int
    free_item_max_usd: int  # the voucher for a complete set
    free_item_terms: str
    referral_credit_max: int


class HuntProgram(BaseModel):
    """Public description of the collection: what can be found now and what it earns. No PII."""

    current_season: HuntSeason
    seasons: list[HuntSeason]
    milestones: HuntMilestones


class FindRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: str = Field(max_length=40, pattern=FRIEND_KEY)
    character: str = Field(max_length=40, pattern=FRIEND_KEY)


class FriendStatus(BaseModel):
    key: str
    name: str
    day: int | None = None
    available: bool = True
    available_from: str
    found: bool
    found_at: str | None = None


class HuntProgress(BaseModel):
    """The signed-in shopper's own collection, rewards and referral code."""

    season_key: str
    season_name: str
    friends: list[FriendStatus]
    season_found: int = Field(ge=0)
    season_total: int = Field(ge=0)
    season_available: int = Field(ge=0)
    total_finds: int = Field(ge=0)
    referral_credits: int = Field(ge=0)
    referral_code: str
    coupon: Coupon | None = None
    rewards: list[Reward] = Field(default_factory=list)
    unlocked: list[Literal["new_find", "already_found", "coupon", "coupon_upgrade", "free_item"]] = Field(default_factory=list)
    next_friend: str | None = None
    next_riddle: str | None = None
    milestones: HuntMilestones


# ------------------------------------------------------------------ restock requests (Problem 9)


class RestockCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    size: Size


class RestockRequest(BaseModel):
    id: int
    product_id: str
    product_name: str
    size: Size
    status: RestockStatus
    created_at: str
    updated_at: str


class RestockList(BaseModel):
    items: list[RestockRequest]
    total: int = Field(ge=0)


class AdminRequester(BaseModel):
    request_id: int
    name: str
    email: str
    created_at: str


class AdminRestockGroup(BaseModel):
    product_id: str
    product_name: str
    size: Size
    open_count: int = Field(ge=0)
    requested_by: list[AdminRequester]


class AdminRestockQueue(BaseModel):
    groups: list[AdminRestockGroup]
    total_open: int = Field(ge=0)
    generated_at: str


class RestockStatusResponse(BaseModel):
    ok: bool = True
    request: RestockRequest


class PasswordPolicy(BaseModel):
    """Published so the front end shows the same rules the server enforces."""

    min_length: int = PASSWORD_MIN
    max_length: int = PASSWORD_MAX
    rules: list[str] = [
        f"At least {PASSWORD_MIN} characters",
        "A lowercase and an uppercase letter",
        "A number",
        "A symbol",
        "No spaces",
        "Not a common password, and not your name or email",
    ]
