"""The shop agent: PydanticAI inside the class safe harness.

- Prompt: prompts/prompt.md, read at startup (one file, grown over later problems).
- Model: Portkey-routed OpenAI model from OPENAI_MODEL (default gpt-5.6-luna). gpt-6 models use
  the Responses API; everything else uses chat completions. The key comes from PORTKEY_API_KEY in
  backend/.env, never from code.
- Tools: tools.py (read-only catalogue and stock). Facts come from tools; the prompt forbids guessing.
- Memory: message_history (DB turns for signed-in shoppers, browser turns for guests) plus a small
  ChatState injected as deps.
- Stopping rules: a finish instruction in the prompt plus UsageLimits(request_limit=12, tool_calls_limit=20).
- Guardrails: prompt guard on the typed text (main.py), allow-listed models, allow-listed product ids
  for cards, no tool can reach users or coupons.
- Audit: every graph node is written to backend/output/audit.jsonl, and the compact trail of the
  loop (time, tool, short args and result, stop reason) is appended to output/audit_trail.json
  (audit.py). Both are append-only and never wiped; cleaned text only.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from pydantic_graph import End

from models import ChatReply, PageLink, ProductQuery
from tools import ChatDeps, register_tools

HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
ALLOWED_MODELS = {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra", "gpt-6-luna"}
LIMITS = UsageLimits(request_limit=12, tool_calls_limit=20)
FALLBACK_REPLY = "Sorry, I hit a snag reaching the shop brain. Try again in a moment, or browse the Products page."

_models: dict[str, Model] = {}
_agent: Agent[ChatDeps, ChatReply] | None = None


# ------------------------------------------------------------------ model (Portkey)


def get_model_name() -> str:
    name = (os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    if name not in ALLOWED_MODELS:
        raise RuntimeError(f"OPENAI_MODEL {name!r} is not allowed. Use one of {sorted(ALLOWED_MODELS)}")
    return name


def build_model(*, fresh: bool = False) -> Model:
    """Cached per model name. `fresh=True` bypasses Portkey's response cache for a true re-ask."""
    name = get_model_name()
    slot = f"{name}|fresh" if fresh else name
    if slot not in _models:
        key = (os.environ.get("PORTKEY_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("PORTKEY_API_KEY is not set. Put it in backend/.env (see .env.example).")
        headers = {"x-portkey-api-key": key}
        if fresh:
            headers["x-portkey-cache-force-refresh"] = "true"
        client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers=headers, max_retries=3)
        provider = OpenAIProvider(openai_client=client)
        _models[slot] = (
            OpenAIResponsesModel(name, provider=provider)
            if name.startswith("gpt-6")
            else OpenAIChatModel(name, provider=provider)
        )
    return _models[slot]


# ------------------------------------------------------------------ agent


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_agent() -> Agent[ChatDeps, ChatReply]:
    """One agent for the process. The model is chosen per run so tests can override it."""
    global _agent
    if _agent is None:
        agent: Agent[ChatDeps, ChatReply] = Agent(
            None,
            deps_type=ChatDeps,
            output_type=ChatReply,
            instructions=load_prompt(),
            retries=2,
            name="campus_customs_shop_agent",
        )

        @agent.instructions
        def shopper_context(ctx: RunContext[ChatDeps]) -> str:
            """Dynamic context injected on every run (Problem 8): who is chatting and what is on
            screen. Only the first name is placed here; last name and email stay behind who_am_i."""
            s = ctx.deps.state
            lines: list[str] = []
            if s.signed_in and s.shopper_first_name:
                lines.append(
                    f"The shopper is signed in. Their first name is {s.shopper_first_name}. "
                    "If they ask who they are or which account they use, call who_am_i and answer from it."
                )
            else:
                lines.append(
                    "The shopper is browsing as a guest (not signed in). If they ask who they are, say nobody is "
                    "signed in and that signing in lets you remember them."
                )
            if s.page_product is not None:
                p = s.page_product
                price = "$" + (format(p.price, ".0f") if float(p.price).is_integer() else format(p.price, ".2f"))
                lines.append(
                    f"The shopper is looking at the product page for \"{p.name}\" (product_id {p.product_id}, "
                    f"{price}, colours: {', '.join(p.colors) if p.colors else 'not listed'}). "
                    "When they say \"this\", \"it\", \"this one\" or \"the one on screen\", they mean that product."
                )
                stock = getattr(p, "stock", None)
                if stock:
                    # Problem 9: the server read this from the database a moment ago, so a stock question
                    # about the item on screen needs no tool round trip (one model call instead of two).
                    levels = ", ".join(
                        f"{lv.size} {'sold out' if lv.quantity <= 0 else ('only ' + str(lv.quantity) + ' left' if lv.quantity <= 5 else 'in stock')}"
                        for lv in stock
                    )
                    lines.append(
                        f"Its stock by size, read from the shop database for this turn: {levels}. "
                        "Answer size and stock questions about this product from that line; mark a sold-out size with the "
                        "ghost (👻) and offer find_alternatives or, for a signed-in shopper, a restock request. "
                        "Call get_product only for its description or tags."
                    )
                else:
                    lines.append("Use its product_id with get_product, get_stock or check_stock before answering.")
            elif s.page_route:
                lines.append(f"The shopper is on the {s.page_route} page of the site.")
            lines.append("Tools you can call this turn: " + ", ".join(s.tool_names) + ".")
            return "\n".join(lines)

        register_tools(agent)
        _agent = agent
    return _agent


def history_from_turns(turns: list[tuple[str, str]]) -> list[ModelMessage]:
    """(role, content) pairs -> PydanticAI messages. Instructions are re-sent every run, so history
    needs no system prompt of its own."""
    out: list[ModelMessage] = []
    for role, content in turns:
        if role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            out.append(ModelResponse(parts=[TextPart(content=content)]))
    return out


@dataclass
class ChatOutcome:
    reply: str
    product_ids: list[str]
    stopped_reason: str
    messages: list[ModelMessage]
    unverified_prices: list[str] | None = None
    go_to: PageLink | None = None


# Problem 9: the agent may offer a page of this site. Only these paths, and only product ids the
# tools really returned, survive validation; everything else is dropped before the browser sees it.
SITE_PATHS = {"/", "/products", "/about", "/login", "/create-account", "/account"}
_PRODUCT_PATH_RE = re.compile(r"^/products/([a-z0-9]+(?:-[a-z0-9]+)*)$")


def validate_page_link(link: PageLink | None, seen: dict[str, Any]) -> PageLink | None:
    """Return a cleaned link to a real page of the site, or None.

    Query strings are allowed only on /products and must pass the same ProductQuery model the API
    uses, so the link can never carry anything the Products page would not accept."""
    if link is None:
        return None
    route = (link.route or "").strip()
    if not route.startswith("/") or route.startswith("//") or "\\" in route:
        return None
    parts = urlsplit(route)
    if parts.scheme or parts.netloc or parts.fragment:
        return None
    path = parts.path.rstrip("/") or "/"
    label = " ".join((link.label or "").split())[:80] or "Open page"
    if path == "/products" and parts.query:
        raw = parse_qs(parts.query, keep_blank_values=False)
        try:
            query = ProductQuery.model_validate({k: v[0] for k, v in raw.items()})
        except Exception:  # noqa: BLE001  (unknown or malformed parameter)
            return None
        kept = {k: v for k, v in query.model_dump().items() if v not in (None, False, "relevance")}
        if isinstance(kept.get("max_price"), float) and kept["max_price"].is_integer():
            kept["max_price"] = int(kept["max_price"])  # "$50", not "$50.0", on the page
        qs = urlencode({k: (str(v).lower() if isinstance(v, bool) else v) for k, v in kept.items()})
        return PageLink(route=f"/products?{qs}" if qs else "/products", label=label, navigate=link.navigate)
    if parts.query:
        return None
    if path in SITE_PATHS:
        return PageLink(route=path, label=label, navigate=link.navigate)
    m = _PRODUCT_PATH_RE.match(path)
    if m and m.group(1) in seen:
        return PageLink(route=path, label=label, navigate=link.navigate)
    return None


_PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
# Built from code points so this file itself never contains the banned character.
_EM_DASH_RE = re.compile(r"\s*[" + chr(0x2014) + chr(0x2015) + r"]\s*")  # em dash, horizontal bar
_EN_DASH_RE = re.compile(chr(0x2013))


def strip_em_dashes(text: str) -> str:
    """House style: no em dashes, ever. A dash between words becomes a comma and a space; an en dash
    becomes a plain hyphen. Doubled punctuation left behind is tidied."""
    out = _EM_DASH_RE.sub(", ", text)
    out = _EN_DASH_RE.sub("-", out)
    out = re.sub(r",\s*([,.;:!?])", r"\1", out)  # ", ." -> "."
    out = re.sub(r"\(\s*,\s*", "(", out)
    out = re.sub(r"^\s*,\s*", "", out, flags=re.M)  # a line that began with a dash
    return re.sub(r"[ \t]{2,}", " ", out)


def unverified_prices(reply: str, seen: dict[str, Any], asked: str = "") -> list[str]:
    """Dollar amounts in the reply that match no product the tools returned this turn.

    A soft guardrail: it cannot prove a price is right, but it catches a price the model made up.
    "10%" style figures are not dollar amounts and are ignored, and so is a figure the shopper
    typed themselves ("under $50" echoed back is their budget, not a price).
    """
    known = {float(p.price) for p in seen.values()}
    for m in _PRICE_RE.finditer(asked):
        try:
            known.add(float(m.group(1)))
        except ValueError:
            continue
    bad: list[str] = []
    for m in _PRICE_RE.finditer(reply):
        try:
            value = float(m.group(1))
        except ValueError:
            continue
        if value not in known:
            bad.append(m.group(0))
    return bad


def _node_summary(node: Any) -> dict[str, Any]:
    """Compact, text-only view of a graph node for the audit trail."""
    out: dict[str, Any] = {"node": type(node).__name__}
    resp = getattr(node, "model_response", None)
    if resp is not None:
        parts = []
        for p in getattr(resp, "parts", []) or []:
            entry: dict[str, Any] = {"part": type(p).__name__}
            if hasattr(p, "tool_name"):
                entry["tool"] = p.tool_name
                entry["args"] = getattr(p, "args", None)
            elif hasattr(p, "content"):
                entry["text"] = str(p.content)[:300]
            parts.append(entry)
        out["parts"] = parts
    req = getattr(node, "request", None)
    if req is not None:
        obs = []
        for p in getattr(req, "parts", []) or []:
            if type(p).__name__ == "ToolReturnPart":
                obs.append({"tool": getattr(p, "tool_name", None), "result": str(getattr(p, "content", ""))[:300]})
            elif type(p).__name__ == "RetryPromptPart":
                obs.append({"retry": str(getattr(p, "content", ""))[:200]})
        if obs:
            out["observations"] = obs
    return out


OUTPUT_TOOL = "final_result"  # PydanticAI's structured-output tool, not one of the shop tools


def _trail_node(audit: Any, node: Any, counts: dict[str, int]) -> None:
    """Problem 12: tool calls, tool results and retries from one graph node, into the compact trail."""
    resp = getattr(node, "model_response", None)
    if resp is not None:
        for p in getattr(resp, "parts", []) or []:
            tool = getattr(p, "tool_name", None)
            if tool and tool != OUTPUT_TOOL:
                counts["tool_calls"] += 1
                audit.trail("tool_call", tool=tool, args=getattr(p, "args", None))
    req = getattr(node, "request", None)
    if req is not None:
        counts["requests"] += 1
        for p in getattr(req, "parts", []) or []:
            name = type(p).__name__
            if name == "ToolReturnPart" and getattr(p, "tool_name", None) != OUTPUT_TOOL:
                audit.trail("tool_result", tool=p.tool_name, result=getattr(p, "content", ""))
            elif name == "RetryPromptPart":
                audit.trail("retry", tool=getattr(p, "tool_name", None), result=getattr(p, "content", ""))


async def run_chat(
    message: str,
    *,
    deps: ChatDeps,
    history: list[ModelMessage],
    model: Model | None = None,
) -> ChatOutcome:
    """One harnessed turn: iterate the graph, audit each node, enforce limits, never raise to the route."""
    agent = build_agent()
    audit = deps.audit
    started = time.perf_counter()
    counts = {"requests": 0, "tool_calls": 0}
    audit.log("user", thought=message, extra={"signed_in": deps.state.signed_in, "history_turns": len(history)})
    audit.trail(
        "turn",
        prompt=message,
        signed_in=deps.state.signed_in,
        page=deps.state.page_route,
        history_turns=len(history),
    )
    stopped_reason = "completed"
    reply = FALLBACK_REPLY
    product_ids: list[str] = []
    new_messages: list[ModelMessage] = list(history)
    bad_prices: list[str] = []
    go_to: PageLink | None = None

    try:
        async with agent.iter(
            message,
            deps=deps,
            message_history=history,
            usage_limits=LIMITS,
            model=model or build_model(),
        ) as run:
            async for node in run:
                if isinstance(node, End):
                    continue
                audit.log("loop", extra=_node_summary(node))
                _trail_node(audit, node, counts)
            result = run.result
            if result is None:
                stopped_reason = "no_result"
            else:
                raw_reply = result.output.reply.strip()
                reply = strip_em_dashes(raw_reply) or FALLBACK_REPLY
                if reply != raw_reply:
                    audit.trail("guard", check="em_dash", result="reply rewritten without the long dash")
                product_ids = [pid for pid in result.output.product_ids if pid in deps.state.seen]
                dropped = [pid for pid in result.output.product_ids if pid not in deps.state.seen]
                if dropped:
                    audit.log("card_check", thought="product ids not returned by any tool were dropped", extra={"dropped": dropped})
                    audit.trail("guard", check="cards", result="dropped ids no tool returned", dropped=dropped)
                go_to = validate_page_link(result.output.go_to, deps.state.seen)
                if go_to is not None:
                    go_to.label = strip_em_dashes(go_to.label)
                if result.output.go_to is not None and go_to is None:
                    audit.log("link_check", thought="page link dropped: not a page of this site", extra={"route": result.output.go_to.route[:120]})
                    audit.trail("guard", check="page_link", result="dropped: not a page of this site", route=result.output.go_to.route[:120])
                new_messages = list(result.all_messages())
                usage = result.usage
                usage = usage() if callable(usage) else usage  # property on current PydanticAI
                bad_prices = unverified_prices(reply, deps.state.seen, asked=message)
                if bad_prices:
                    audit.log("price_check", thought="dollar amounts not backed by a tool result", extra={"amounts": bad_prices})
                    audit.trail("guard", check="price", result="dollar amounts not backed by a tool result", amounts=bad_prices)
                audit.log(
                    "final",
                    thought=reply,
                    extra={"product_ids": product_ids, "go_to": go_to.route if go_to else None, "usage": str(usage)},
                )
                audit.trail("reply", text=reply, product_ids=product_ids or None, go_to=go_to.route if go_to else None)
    except UsageLimitExceeded as exc:
        stopped_reason = "usage_limit"
        reply = "I looked at a lot of items and ran out of room. Could you narrow it down, say a category or a colour?"
        audit.log("stop", thought=str(exc)[:200])
    except Exception as exc:  # noqa: BLE001
        stopped_reason = type(exc).__name__
        audit.log("error", thought=f"{type(exc).__name__}: {str(exc)[:200]}")

    audit.log("harness_complete", thought=stopped_reason)
    audit.trail(
        "stop",
        stop_reason=stopped_reason,
        requests=counts["requests"],
        tool_calls=counts["tool_calls"],
        ms=int((time.perf_counter() - started) * 1000),
    )
    return ChatOutcome(
        reply=reply,
        product_ids=product_ids,
        stopped_reason=stopped_reason,
        messages=new_messages,
        unverified_prices=bad_prices,
        go_to=go_to,
    )
