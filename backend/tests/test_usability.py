"""Problem 9: usability improvements. Products sort and size chips, the hidden-friends collection
with its milestones and referrals, restock requests (tool, routes, admin queue), sold-out
alternatives, the agent's page links and the clue tool. Offline: TestModel, throwaway database."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_REAL_DATA = _HERE.parent.parent / "data"
_TMP = Path(tempfile.mkdtemp(prefix="cc-usability-test-"))
shutil.copy(_REAL_DATA / "campus_customs.db", _TMP / "campus_customs.db")
(_TMP / "products").mkdir()
os.environ["DATA_DIR"] = str(_TMP)
os.environ["SESSION_SECRET"] = "test-secret-not-for-production"
os.environ["HUNT_DATE"] = "2026-10-31"  # every daily friend is out

from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
import hunt  # noqa: E402
import main  # noqa: E402
import tools  # noqa: E402
from agent import validate_page_link  # noqa: E402
from models import PageLink  # noqa: E402

STRONG = "Pumpkin-Lantern-77!"
HOODIE = "basic-hoodie-big-yale"


@pytest.fixture(autouse=True)
def _reset_limits():
    main.auth_ip_limiter.reset()
    main.auth_email_limiter.reset()
    main.chat_limiter.reset()
    main.hunt_limiter.reset()
    yield


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _signup(client, first="Mei", referral: str | None = None) -> tuple[dict, dict]:
    email = f"{first.lower()}-{time.time_ns()}@example.edu"
    body = {"first_name": first, "last_name": "Kusakabe", "email": email, "password": STRONG, "confirm_password": STRONG}
    if referral:
        body["referral_code"] = referral
    r = client.post("/auth/signup", json=body)
    assert r.status_code == 201, r.text
    return r.json(), {"Authorization": f"Bearer {r.json()['token']}"}


def _sold_out_pair() -> tuple[str, str]:
    with db.connect() as con:
        row = con.execute("SELECT product_id, size FROM inventory WHERE quantity = 0 LIMIT 1").fetchone()
    return row["product_id"], row["size"]


def _in_stock_pair() -> tuple[str, str]:
    with db.connect() as con:
        row = con.execute("SELECT product_id, size FROM inventory WHERE quantity > 5 LIMIT 1").fetchone()
    return row["product_id"], row["size"]


# ------------------------------------------------------------------ front-end pick 2: products you can narrow


def test_products_sort_and_size_chips(client):
    cheap = client.get("/products?sort=price_asc&category=t-shirt").json()
    prices = [p["price"] for p in cheap["items"]]
    assert prices == sorted(prices) and cheap["total"] > 1
    dear = client.get("/products?sort=price_desc").json()["items"]
    assert dear[0]["price"] >= dear[-1]["price"]
    capped = client.get("/products?max_price=40&in_stock=true").json()["items"]
    assert capped and all(p["price"] <= 40 and p["total_stock"] > 0 for p in capped)
    # every card carries the sizes in stock, and they agree with the inventory table
    item = client.get(f"/products?q={HOODIE.split('-')[0]}").json()["items"][0]
    detail = client.get(f"/products/{item['product_id']}").json()
    assert item["sizes_in_stock"] == [s["size"] for s in detail["stock"] if s["quantity"] > 0]
    assert client.get("/products?sort=cheapest").status_code == 422
    assert client.get("/products?order=asc").status_code == 422


# ------------------------------------------------------------------ front-end pick 1: hidden friends collection


def test_hunt_program_is_public_and_pii_free(client):
    r = client.get("/hunt")
    assert r.status_code == 200
    body = r.json()
    season = body["current_season"]
    assert season["status"] == "active" and season["daily"] is True and len(season["friends"]) == 31
    assert [f["day"] for f in season["friends"]] == list(range(1, 32))
    assert season["friends"][0]["key"] == "totoro-witch" and season["friends"][1]["key"] == "chu-ghost"
    assert season["friends"][30]["key"] == "chibi-pumpkin" and len({f["key"] for f in season["friends"]}) == 31
    assert all(f["riddle"] and f["home_route"].startswith("/") for f in season["friends"])
    assert season["today"] == "10-31" and season["available_count"] == 31
    # the seven characters in eight costumes, home pages rotating through the site
    cast = {"totoro", "chu", "chibi", "catbus", "labubu", "soot", "noface"}
    assert {f["key"].split("-")[0] for f in season["friends"]} == cast
    assert len({f["key"].split("-")[1] for f in season["friends"]}) == 8
    assert [f["home_route"] for f in season["friends"][:4]] == ["/", "/products", "/about", "/products/*"]
    for s in body["seasons"]:
        assert {f["key"].split("-")[0] for f in s["friends"]} <= cast
    assert body["milestones"]["coupon_at"] == 3 and body["milestones"]["coupon_pct"] == 10
    assert body["milestones"]["lift_at"] == 10 and body["milestones"]["lift_pct"] == 15
    assert body["milestones"]["free_item_max_usd"] == 100 and "in-stock" in body["milestones"]["free_item_terms"]
    assert body["milestones"]["referral_credit_max"] == 3
    assert [s["status"] for s in body["seasons"]] == ["active", "coming", "coming"]
    assert "email" not in r.text and "user" not in r.text


def test_daily_friends_unlock_one_per_day(client, monkeypatch):
    monkeypatch.setenv("HUNT_DATE", "2026-10-05")
    season = client.get("/hunt").json()["current_season"]
    assert season["available_count"] == 5 and season["today"] == "10-05"
    assert [f["available"] for f in season["friends"][:6]] == [True] * 5 + [False]
    assert season["friends"][5]["available_from"] == "10-06"
    _, h = _signup(client, "Daily")
    locked = season["friends"][5]["key"]
    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": locked}, headers=h).status_code == 404
    ok = client.post("/me/hunt/finds", json={"season": season["key"], "character": season["friends"][4]["key"]}, headers=h).json()
    assert ok["unlocked"] == ["new_find"] and ok["season_available"] == 5 and ok["season_total"] == 31
    # the chase points at the earliest available friend not yet found, never a locked one
    assert ok["next_friend"] == season["friends"][0]["name"]
    monkeypatch.setenv("HUNT_DATE", "2026-11-02")
    assert client.get("/hunt").json()["current_season"]["available_count"] == 31


def test_finds_earn_coupon_then_upgrade_and_never_a_second_code(client):
    _, h = _signup(client, "Satsuki")
    season = client.get("/hunt").json()["current_season"]
    keys = [f["key"] for f in season["friends"]]

    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[0]}).status_code == 401
    assert client.post("/me/hunt/finds", json={"season": season["key"], "character": "pikachu"}, headers=h).status_code == 404
    assert client.post("/me/hunt/finds", json={"season": "winter", "character": keys[0]}, headers=h).status_code == 404

    first = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[0]}, headers=h).json()
    assert first["unlocked"] == ["new_find"] and first["season_found"] == 1 and first["coupon"] is None
    assert first["next_friend"] == season["friends"][1]["name"] and first["next_riddle"] == season["friends"][1]["riddle"]
    assert first["referral_code"] and len(first["referral_code"]) == 8

    again = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[0]}, headers=h).json()
    assert again["unlocked"] == ["already_found"] and again["season_found"] == 1

    client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[1]}, headers=h)
    third = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[2]}, headers=h).json()
    assert third["unlocked"] == ["new_find", "coupon"]
    assert third["coupon"]["discount_pct"] == 10 and third["coupon"]["scope"] == "one_item"
    code = third["coupon"]["code"]
    assert code.startswith("CHIBI10-")  # day 3 is Zombie Chibi Totoro

    for n, k in enumerate(keys[3:-1], start=4):
        mid = client.post("/me/hunt/finds", json={"season": season["key"], "character": k}, headers=h).json()
        expected = ["new_find", "coupon_upgrade"] if n == 10 else ["new_find"]
        assert mid["unlocked"] == expected, (n, mid["unlocked"])
        assert mid["coupon"]["discount_pct"] == (15 if n >= 10 else 10) and mid["rewards"] == []
    last = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[-1]}, headers=h).json()
    assert last["unlocked"] == ["new_find", "free_item"]
    assert last["coupon"]["code"] == code and last["coupon"]["discount_pct"] == 15
    assert last["season_found"] == len(keys) == 31 and last["next_friend"] is None
    voucher = last["rewards"][0]
    assert voucher["kind"] == "free_item" and voucher["max_value_usd"] == 100 and voucher["code"].startswith("FREEITEM-")
    assert "purchase of another item" in voucher["terms"] and "while supplies last" in voucher["terms"]

    mine = client.get("/me/hunt", headers=h).json()
    assert mine["coupon"]["code"] == code and mine["total_finds"] == len(keys) and mine["unlocked"] == []
    assert all(f["found"] for f in mine["friends"])


def test_ten_finds_across_seasons_lift_the_coupon_once(client):
    me, h = _signup(client, "Kiki")
    season = client.get("/hunt").json()["current_season"]
    keys = [f["key"] for f in season["friends"]]
    for i in range(6):  # earlier seasons, written straight to the table
        assert db.add_find(me["user"]["id"], "test-season", f"friend-{i}")
    for k in keys[:3]:
        client.post("/me/hunt/finds", json={"season": season["key"], "character": k}, headers=h)
    tenth = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[3]}, headers=h).json()
    assert tenth["total_finds"] == 10
    assert tenth["unlocked"] == ["new_find", "coupon_upgrade"] and tenth["coupon"]["discount_pct"] == 15
    assert tenth["rewards"] == []  # the voucher needs the whole set, not ten finds
    eleventh = client.post("/me/hunt/finds", json={"season": season["key"], "character": keys[4]}, headers=h).json()
    assert eleventh["unlocked"] == ["new_find"] and eleventh["coupon"]["discount_pct"] == 15
    assert db.grant_reward(me["user"]["id"], "free_item", "FREEITEM-ONCE", 100) is not None
    assert db.grant_reward(me["user"]["id"], "free_item", "FREEITEM-AGAIN", 100) is None  # one per shopper


def test_referrals_credit_the_referrer_up_to_three(client):
    ref, h = _signup(client, "Haku")
    code = client.get("/me/hunt", headers=h).json()["referral_code"]
    for i in range(4):
        new, _ = _signup(client, f"Chihiro{i}", referral=code.lower())
        assert new["user"]["id"] != ref["user"]["id"]
    mine = client.get("/me/hunt", headers=h).json()
    assert mine["referral_credits"] == 3 and mine["total_finds"] == 3
    assert db.get_user_by_id(new["user"]["id"]).referred_by == ref["user"]["id"]
    # an unknown code never blocks a signup, a malformed one is a 422
    _signup(client, "Lin", referral="NOPE1234")
    r = client.post(
        "/auth/signup",
        json={"first_name": "Yubaba", "last_name": "Boss", "email": f"y-{time.time_ns()}@example.edu", "password": STRONG, "confirm_password": STRONG, "referral_code": "a b"},
    )
    assert r.status_code == 422


def test_delete_account_removes_finds_rewards_and_requests(client):
    me, h = _signup(client, "Mei2")
    season = client.get("/hunt").json()["current_season"]
    client.post("/me/hunt/finds", json={"season": season["key"], "character": season["friends"][0]["key"]}, headers=h)
    pid, size = _sold_out_pair()
    assert client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h).status_code == 201
    assert client.delete("/me", headers=h).status_code == 200
    assert db.list_finds(me["user"]["id"]) == [] and db.list_restock_requests(me["user"]["id"]) == []
    assert db.get_user_by_id(me["user"]["id"]) is None


# ------------------------------------------------------------------ backend pick 1: restock requests


def test_restock_tool_only_writes_for_a_sold_out_size_and_a_signed_in_shopper(client):
    me, _ = _signup(client, "Ponyo")
    uid = me["user"]["id"]
    sold_pid, sold_size = _sold_out_pair()
    in_pid, in_size = _in_stock_pair()

    guest = tools.create_restock(None, sold_pid, sold_size)
    assert guest.ok is False and "sign" in guest.error.lower()
    assert tools.create_restock(uid, "ghost-hoodie", "M").ok is False
    stocked = tools.create_restock(uid, in_pid, in_size)
    assert stocked.ok is False and "in stock" in stocked.error

    first = tools.create_restock(uid, sold_pid, sold_size)
    assert first.ok and first.outcome == "created" and first.request_id and first.open_requests == 1
    again = tools.create_restock(uid, sold_pid, sold_size)
    assert again.ok and again.outcome == "already_open" and again.request_id == first.request_id
    assert db.count_open_restock_requests(uid) == 1
    assert "request_restock" in tools.TOOL_NAMES and "find_alternatives" in tools.TOOL_NAMES and "hiding_clue" in tools.TOOL_NAMES


def test_shopper_sees_and_cancels_own_requests_only(client):
    _, h1 = _signup(client, "Sosuke")
    _, h2 = _signup(client, "Lisa")
    pid, size = _sold_out_pair()
    created = client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h1)
    assert created.status_code == 201
    rid = created.json()["request"]["id"]
    assert created.json()["request"]["status"] == "open" and created.json()["request"]["product_name"]
    dup = client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h1)
    assert dup.status_code == 201 and dup.json()["request"]["id"] == rid
    in_pid, in_size = _in_stock_pair()
    assert client.post("/me/restock-requests", json={"product_id": in_pid, "size": in_size}, headers=h1).status_code == 409
    assert client.post("/me/restock-requests", json={"product_id": pid, "size": size, "note": "x"}, headers=h1).status_code == 422

    assert client.get("/me/restock-requests", headers=h1).json()["total"] == 1
    assert client.get("/me/restock-requests", headers=h2).json()["total"] == 0
    assert client.get("/me/restock-requests").status_code == 401
    assert client.delete(f"/me/restock-requests/{rid}", headers=h2).status_code == 404  # not theirs
    cancelled = client.delete(f"/me/restock-requests/{rid}", headers=h1)
    assert cancelled.status_code == 200 and cancelled.json()["request"]["status"] == "cancelled"
    # cancelled requests leave the way clear for a new one
    assert client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h1).json()["request"]["id"] != rid


def test_admin_queue_groups_by_product_and_size(client, monkeypatch):
    staff, hs = _signup(client, "Staff")
    _, h1 = _signup(client, "Nausicaa")
    _, h2 = _signup(client, "Asbel")
    pid, size = _sold_out_pair()
    client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h1)
    client.post("/me/restock-requests", json={"product_id": pid, "size": size}, headers=h2)

    assert client.get("/admin/restock-requests", headers=h1).status_code == 403
    assert client.get("/admin/restock-requests").status_code == 401
    monkeypatch.setattr(main, "ADMIN_EMAILS", {staff["user"]["email"]})
    assert client.get("/me", headers=hs).json()["is_admin"] is True
    assert client.get("/me", headers=h1).json()["is_admin"] is False

    queue = client.get("/admin/restock-requests", headers=hs).json()
    group = next(g for g in queue["groups"] if g["product_id"] == pid and g["size"] == size)
    assert group["open_count"] >= 2 and len(group["requested_by"]) == group["open_count"]
    assert all(w["name"] and "@" in w["email"] for w in group["requested_by"])
    assert queue["total_open"] >= 2

    csv_text = client.get("/admin/restock-requests.csv", headers=hs)
    assert csv_text.status_code == 200 and csv_text.headers["content-type"].startswith("text/csv")
    assert csv_text.text.splitlines()[0] == "product_id,product_name,size,open_requests,request_id,requested_by,email,requested_at"
    assert pid in csv_text.text

    rid = group["requested_by"][0]["request_id"]
    done = client.post(f"/admin/restock-requests/{rid}/ordered", headers=hs)
    assert done.status_code == 200 and done.json()["request"]["status"] == "ordered"
    after = client.get("/admin/restock-requests", headers=hs).json()
    later = next((g for g in after["groups"] if g["product_id"] == pid and g["size"] == size), None)
    assert later is None or later["open_count"] == group["open_count"] - 1
    assert client.post("/admin/restock-requests/999999/ordered", headers=hs).status_code == 404


# ------------------------------------------------------------------ backend pick 2: fewer dead ends and clicks


def test_alternatives_have_the_size_in_stock_and_share_the_category():
    pid, size = _sold_out_pair()
    original = db.get_product(pid)
    result, covered = tools.lookup_alternatives(pid, size)
    assert result.ok and result.wanted_in_stock is False and result.name == original.name
    assert [b.product_id for b in result.items] == [p.product_id for p in covered]
    assert 0 < len(result.items) <= 5
    for b in result.items:
        assert b.product_id != pid and size in b.sizes_in_stock and b.category == original.category
    gaps = [abs(b.price - original.price) for b in result.items]
    assert gaps == sorted(gaps)
    assert tools.lookup_alternatives("ghost-hoodie", "M")[0].ok is False


def test_page_links_are_validated_against_the_site():
    seen = {HOODIE: object()}
    ok = validate_page_link(PageLink(route="/products?category=hoodie&max_price=50&sort=price_asc", label=" Hoodies  under $50 "), seen)
    assert ok is not None and ok.route == "/products?category=hoodie&max_price=50&sort=price_asc" and ok.label == "Hoodies under $50"
    assert validate_page_link(PageLink(route="/products?max_price=49.5", label="x"), seen).route == "/products?max_price=49.5"
    assert validate_page_link(PageLink(route="/products?in_stock=true", label="x"), seen).route == "/products?in_stock=true"
    assert validate_page_link(PageLink(route=f"/products/{HOODIE}", label="Open it", navigate=True), seen).navigate is True
    assert validate_page_link(PageLink(route="/account", label=""), seen).label == "Open page"
    for bad in (
        "/products/not-seen-id",
        "/products?category=hats",
        "/products?utm=1",
        "/admin/restock-requests",
        "https://evil.example/products",
        "//evil.example",
        "javascript:alert(1)",
        "/about#x",
        "/about?x=1",
    ):
        assert validate_page_link(PageLink(route=bad, label="x"), seen) is None, bad
    assert validate_page_link(None, seen) is None


def test_chat_returns_a_validated_link_or_none(client):
    from pydantic_ai.models.test import TestModel

    import agent as agent_module

    with agent_module.build_agent().override(model=TestModel()):
        r = client.post("/chat", json={"message": "take me to the hoodies"})
    assert r.status_code == 200
    body = r.json()
    assert "go_to" in body
    if body["go_to"] is not None:
        assert body["go_to"]["route"].startswith("/") and body["go_to"]["label"]


def test_page_product_stock_is_in_the_dynamic_context_so_no_tool_call_is_needed():
    from pydantic_ai.models.test import TestModel

    import agent as agent_module
    from audit import AuditLogger

    detail = db.get_product(HOODIE)
    state = tools.ChatState(page_route=f"/products/{HOODIE}", page_product=detail)
    deps = tools.ChatDeps(state=state, audit=AuditLogger(run_id="t", path=_TMP / "a.jsonl"))
    ag = agent_module.build_agent()
    with ag.override(model=TestModel()):
        import asyncio

        outcome = asyncio.run(agent_module.run_chat("do you have this in M?", deps=deps, history=[]))
    assert outcome.stopped_reason == "completed"
    # The instructions sent with the first request carry the product's stock by size from the database.
    from pydantic_ai.messages import ModelRequest

    first = next(m for m in outcome.messages if isinstance(m, ModelRequest))
    text = first.instructions or ""
    assert "stock by size" in text and HOODIE in text
    for level in detail.stock:
        assert f"{level.size} " in text


def test_clue_tool_reads_progress_from_the_server(client):
    me, h = _signup(client, "Arrietty")
    season = client.get("/hunt").json()["current_season"]
    guest = tools.lookup_clue(None)
    assert guest.ok and guest.signed_in is False and guest.riddle == season["friends"][0]["riddle"]
    before = tools.lookup_clue(me["user"]["id"])
    assert before.found == 0 and before.total == 31 and before.next_friend == season["friends"][0]["name"]
    client.post("/me/hunt/finds", json={"season": season["key"], "character": season["friends"][0]["key"]}, headers=h)
    after = tools.lookup_clue(me["user"]["id"])
    assert after.found == 1 and after.next_friend == season["friends"][1]["name"] and after.riddle == season["friends"][1]["riddle"]


def test_current_season_is_the_latest_drawable_one(monkeypatch):
    from datetime import date

    monkeypatch.delenv("HUNT_SEASON", raising=False)
    monkeypatch.setenv("HUNT_DATE", "2026-10-19")
    assert hunt.today() == date(2026, 10, 19)
    assert hunt.current_season(date(2026, 10, 19)).key == "halloween"
    assert hunt.current_season(date(2026, 11, 20)).key == "halloween"  # thanksgiving art not ready yet
    assert hunt.current_season(date(2026, 3, 1)).key == "halloween"
    assert hunt.is_home("/products/*", "/products/basic-hoodie-big-yale") and not hunt.is_home("/products/*", "/products")
    assert hunt.is_home("/", "/") and not hunt.is_home("/", "/about")
