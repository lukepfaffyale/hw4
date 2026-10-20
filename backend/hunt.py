"""Hidden friends (Problem 9): a seasonal collection that rewards time on the site and return visits.

Rules in one place so the API, the agent's clue tool and the docs agree:

- The cast is always four characters (Totoro, Labubu, a Soot Sprite and No-Face) in that season's
  trick-or-treat costumes. The Halloween set is 31 friends, one for each day of October: a new
  friend becomes findable each day (and stays findable until the set ends), so there is a reason
  to come back daily. Each friend has a home page where it always hides until found, and a riddle
  that points at that page.
- Three finds in a season earn the shopper's single coupon (10% off one item). Ten finds across
  seasons (friend referrals count, up to three) lift that same coupon to 15%. Finding a whole set
  earns the free-item voucher: a free item with the purchase of another, up to $100 in value,
  in-stock items only, while supplies last. Codes are class-project codes, not redeemable at the store.
- The programme is defined in code, not in the database; only finds, coupons and rewards are stored.
  A new season is added here with its art in the front end; until a later season is marked ready the
  current one simply carries on, so the site never shows a set it cannot draw.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import date

import db
from models import (
    FREE_ITEM_TERMS,
    ClueResult,
    FriendStatus,
    HuntFriend,
    HuntMilestones,
    HuntProgram,
    HuntProgress,
    HuntSeason,
)

COUPON_AT = 3
COUPON_PCT = 10
LIFT_AT = 10
LIFT_PCT = 15
FREE_ITEM_MAX_USD = 100
REFERRAL_CREDIT_MAX = 3
REFERRAL_CHARACTER = "referral"

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


@dataclass(frozen=True)
class Friend:
    key: str
    name: str
    home_route: str
    riddle: str
    day: int = 0  # for daily sets: the day of the season's start month this friend unlocks


@dataclass(frozen=True)
class Season:
    key: str
    name: str
    starts: tuple[int, int]  # (month, day)
    ends: tuple[int, int]
    friends: tuple[Friend, ...]
    art_ready: bool  # the front end can draw every friend in this set
    daily: bool = False  # friends unlock one per day of the start month


# The cast and the costumes. The front end draws `<character>-<costume>`; anything it cannot
# draw shows as a silhouette, so a new costume is added here and in characters.tsx together.
CHARACTERS: tuple[tuple[str, str], ...] = (
    ("totoro", "Totoro"),
    ("chu", "Chu Totoro"),  # the middle, blue-grey sibling
    ("chibi", "Chibi Totoro"),  # the tiny white one
    ("catbus", "Catbus"),
    ("labubu", "Labubu"),
    ("soot", "Soot Sprite"),
    ("noface", "No-Face"),
)
HALLOWEEN_COSTUMES: tuple[tuple[str, str, str], ...] = (
    ("witch", "Witch", "A pointed hat and a crooked broom."),
    ("ghost", "Ghost", "A sheet with two eye holes, going boo."),
    ("zombie", "Zombie", "Arms out, shuffling, a little green."),
    ("skeleton", "Skeleton", "Painted bones that rattle when I bob."),
    ("vampire", "Vampire", "A cape, two fangs and a grin."),
    ("mummy", "Mummy", "Wrapped head to toe in bandages."),
    ("pumpkin", "Pumpkin", "A carved pumpkin on my head and a bucket of candy."),
    ("devil", "Devil", "Little red horns and a toy pitchfork."),
)
# Home pages rotate day by day, so the chase loops through the whole site.
PAGES: tuple[tuple[str, str], ...] = (
    ("/", "I wait by the front door, where every visit starts."),
    ("/products", "I drift between the racks where the hoodies hang. Watch the corners."),
    ("/about", "I hide where the shop tells its own story."),
    ("/products/*", "I curl up on a single item's page. Pick any one and look closely."),
)


def _daily_friends(costumes: tuple[tuple[str, str, str], ...], days: int) -> tuple[Friend, ...]:
    """One friend per day. Character and costume both advance each day (7 characters, 8 costumes),
    so no pairing repeats inside a month and neighbouring days never share a character."""
    out: list[Friend] = []
    for day in range(1, days + 1):
        chkey, chname = CHARACTERS[(day - 1) % len(CHARACTERS)]
        ckey, cname, cline = costumes[(day - 1) % len(costumes)]
        route, pline = PAGES[(day - 1) % len(PAGES)]
        out.append(Friend(key=f"{chkey}-{ckey}", name=f"{cname} {chname}", home_route=route, riddle=f"{cline} {pline}", day=day))
    assert len({f.key for f in out}) == len(out), "a character-costume pairing repeated"
    return tuple(out)


SEASONS: tuple[Season, ...] = (
    Season(
        key="halloween",
        name="Halloween set",
        starts=(10, 1),
        ends=(11, 5),
        art_ready=True,
        daily=True,
        friends=_daily_friends(HALLOWEEN_COSTUMES, 31),
    ),
    Season(
        key="thanksgiving",
        name="Thanksgiving set",
        starts=(11, 6),
        ends=(11, 30),
        art_ready=False,
        friends=(
            Friend("totoro-pilgrim", "Pilgrim Totoro", "/", "A buckled hat at the front door."),
            Friend("labubu-turkey", "Turkey Labubu", "/products", "Tail feathers between the racks."),
            Friend("soot-pie", "Pie Soot Sprite", "/about", "Something warm where the shop tells its story."),
            Friend("noface-harvest", "Harvest No-Face", "/products/*", "A basket of leaves on one item's page."),
        ),
    ),
    Season(
        key="winter",
        name="Winter set",
        starts=(12, 1),
        ends=(1, 6),
        art_ready=False,
        friends=(
            Friend("totoro-santa", "Santa Totoro", "/", "A red hat at the front door."),
            Friend("labubu-elf", "Elf Labubu", "/products", "Pointy ears between the racks."),
            Friend("soot-snowman", "Snowman Soot Sprite", "/about", "A carrot nose where the shop tells its story."),
            Friend("noface-reindeer", "Reindeer No-Face", "/products/*", "Antlers on one item's page."),
        ),
    ),
)

_BY_KEY = {s.key: s for s in SEASONS}


# ------------------------------------------------------------------ dates and availability


def today() -> date:
    """The programme's idea of today. HUNT_DATE=YYYY-MM-DD in .env pins it for demos and tests."""
    raw = (os.environ.get("HUNT_DATE") or "").strip()
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return date.today()


def _mmdd(t: tuple[int, int]) -> str:
    return f"{t[0]:02d}-{t[1]:02d}"


def current_season(on: date | None = None) -> Season:
    """The season whose friends can be found now. HUNT_SEASON in .env forces one (for a demo).

    Only seasons with art are eligible; the most recently started one wins, so the active set
    carries on past its end date until the next set is actually drawable."""
    forced = (os.environ.get("HUNT_SEASON") or "").strip()
    if forced in _BY_KEY and _BY_KEY[forced].art_ready:
        return _BY_KEY[forced]
    on = on or today()
    ready = [s for s in SEASONS if s.art_ready]
    started = [s for s in ready if s.starts <= (on.month, on.day)]
    pool = started or ready
    return max(pool, key=lambda s: s.starts)


def season_by_key(key: str) -> Season | None:
    return _BY_KEY.get(key)


def unlock_date(season: Season, friend: Friend) -> tuple[int, int]:
    return (season.starts[0], friend.day) if season.daily and friend.day else season.starts


def is_available(season: Season, friend: Friend, on: date | None = None) -> bool:
    """A daily friend can be found from its day onward (and after the month ends, all of them)."""
    if not season.daily or not friend.day:
        return True
    on = on or today()
    return (on.month, on.day) >= unlock_date(season, friend)


def available_friends(season: Season, on: date | None = None) -> list[Friend]:
    return [f for f in season.friends if is_available(season, f, on)]


def is_home(home_route: str, pathname: str) -> bool:
    if home_route.endswith("/*"):
        base = home_route[:-2]
        return pathname.startswith(base + "/") and len(pathname) > len(base) + 1
    return pathname == home_route


def _friend_model(season: Season, f: Friend, on: date) -> HuntFriend:
    return HuntFriend(
        key=f.key,
        name=f.name,
        home_route=f.home_route,
        riddle=f.riddle,
        day=f.day or None,
        available=is_available(season, f, on),
        available_from=_mmdd(unlock_date(season, f)),
    )


def _season_model(season: Season, current: Season, on: date) -> HuntSeason:
    if season.key == current.key:
        status = "active"
    elif season.starts > current.starts or (season.starts < current.starts and season.key == "winter" and current.key != "winter"):
        status = "coming"
    else:
        status = "past"
    friends = [_friend_model(season, f, on) for f in season.friends]
    return HuntSeason(
        key=season.key,
        name=season.name,
        starts=_mmdd(season.starts),
        ends=_mmdd(season.ends),
        status=status,
        daily=season.daily,
        today=_mmdd((on.month, on.day)),
        available_count=sum(1 for f in friends if f.available),
        friends=friends,
    )


def milestones() -> HuntMilestones:
    return HuntMilestones(
        coupon_at=COUPON_AT,
        coupon_pct=COUPON_PCT,
        lift_at=LIFT_AT,
        lift_pct=LIFT_PCT,
        free_item_max_usd=FREE_ITEM_MAX_USD,
        free_item_terms=FREE_ITEM_TERMS,
        referral_credit_max=REFERRAL_CREDIT_MAX,
    )


def program() -> HuntProgram:
    on = today()
    current = current_season(on)
    return HuntProgram(
        current_season=_season_model(current, current, on),
        seasons=[_season_model(s, current, on) for s in SEASONS],
        milestones=milestones(),
    )


# ------------------------------------------------------------------ codes


def _tail(n: int = 4) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(n))


def make_coupon_code(character: str) -> str:
    word = character.split("-")[0].upper()[:8] or "FRIEND"
    return f"{word}{COUPON_PCT}-{_tail()}"


def make_reward_code() -> str:
    return f"FREEITEM-{_tail(6)}"


# ------------------------------------------------------------------ progress and milestones


def _evaluate(user_id: int, season: Season, trigger: str) -> list[str]:
    """Grant whatever the shopper has now earned. Idempotent: nothing is granted twice."""
    unlocked: list[str] = []
    finds = db.list_finds(user_id)
    season_found = [f for f in finds if f.season == season.key and f.source == "found"]
    total = len(finds)

    coupon = db.get_coupon(user_id)
    if len(season_found) >= COUPON_AT and coupon is None:
        coupon = db.claim_coupon(user_id, trigger, lambda: make_coupon_code(trigger))
        unlocked.append("coupon")
    if total >= LIFT_AT and coupon is not None and coupon.discount_pct < LIFT_PCT:
        db.upgrade_coupon(user_id, LIFT_PCT)
        unlocked.append("coupon_upgrade")
    if len(season_found) >= len(season.friends) and db.grant_reward(user_id, "free_item", make_reward_code(), FREE_ITEM_MAX_USD) is not None:
        unlocked.append("free_item")
    return unlocked


def _next_unfound(season: Season, found: set[str], on: date) -> Friend | None:
    """The chase: the earliest available friend not yet found."""
    return next((f for f in season.friends if f.key not in found and is_available(season, f, on)), None)


def progress(user: db.UserRecord, unlocked: list[str] | None = None) -> HuntProgress:
    on = today()
    season = current_season(on)
    finds = db.list_finds(user.id)
    found_at = {f.character: f.created_at for f in finds if f.season == season.key and f.source == "found"}
    friends = [
        FriendStatus(
            key=f.key,
            name=f.name,
            day=f.day or None,
            available=is_available(season, f, on),
            available_from=_mmdd(unlock_date(season, f)),
            found=f.key in found_at,
            found_at=found_at.get(f.key),
        )
        for f in season.friends
    ]
    nxt = _next_unfound(season, set(found_at), on)
    return HuntProgress(
        season_key=season.key,
        season_name=season.name,
        friends=friends,
        season_found=len(found_at),
        season_total=len(season.friends),
        season_available=sum(1 for f in friends if f.available),
        total_finds=len(finds),
        referral_credits=sum(1 for f in finds if f.source == "referral"),
        referral_code=user.referral_code or "",
        coupon=db.get_coupon(user.id),
        rewards=db.list_rewards(user.id),
        unlocked=list(unlocked or []),  # type: ignore[arg-type]
        next_friend=nxt.name if nxt else None,
        next_riddle=nxt.riddle if nxt else None,
        milestones=milestones(),
    )


def record_find(user: db.UserRecord, season_key: str, character: str) -> HuntProgress | None:
    """A signed-in shopper tapped a friend. Returns None when the friend is not findable now
    (wrong season, unknown key, or a daily friend whose day has not come)."""
    on = today()
    season = current_season(on)
    if season_key != season.key:
        return None
    friend = next((f for f in season.friends if f.key == character), None)
    if friend is None or not is_available(season, friend, on):
        return None
    unlocked = ["new_find"] if db.add_find(user.id, season.key, character) else ["already_found"]
    unlocked += _evaluate(user.id, season, character)
    return progress(user, unlocked)


def credit_referral(referrer: db.UserRecord, new_user: db.UserRecord) -> bool:
    """A new account used `referrer`'s code: one credit toward the free item, capped."""
    season = current_season()
    credited = db.add_referral_credit(referrer.id, new_user.id, season.key, REFERRAL_CREDIT_MAX)
    if credited:
        _evaluate(referrer.id, season, REFERRAL_CHARACTER)
    return credited


# ------------------------------------------------------------------ the agent's clue


def clue(user: db.UserRecord | None) -> ClueResult:
    """The riddle for the next unfound friend. It hints at a page, never the exact spot."""
    on = today()
    season = current_season(on)
    available = available_friends(season, on)
    if user is None:
        first = available[0] if available else None
        return ClueResult(
            ok=True,
            signed_in=False,
            season_name=season.name,
            found=0,
            total=len(season.friends),
            next_friend=first.name if first else None,
            riddle=first.riddle if first else None,
            note="Guests can find friends too; signing in saves the finds and unlocks the rewards."
            + (f" {len(available)} of {len(season.friends)} friends are out so far this season." if season.daily else ""),
        )
    found = {f.character for f in db.list_finds(user.id) if f.season == season.key and f.source == "found"}
    nxt = _next_unfound(season, found, on)
    if nxt is None:
        note = (
            "Every friend that is out so far has been found. A new one arrives tomorrow."
            if season.daily and len(available) < len(season.friends)
            else "The whole set is found. The next set arrives with the next season."
        )
        return ClueResult(ok=True, signed_in=True, season_name=season.name, found=len(found), total=len(season.friends), note=note)
    return ClueResult(
        ok=True,
        signed_in=True,
        season_name=season.name,
        found=len(found),
        total=len(season.friends),
        next_friend=nxt.name,
        riddle=nxt.riddle,
        note=f"{len(available)} of {len(season.friends)} friends are out so far this season." if season.daily else None,
    )
