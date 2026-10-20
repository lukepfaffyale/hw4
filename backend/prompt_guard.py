"""Drop LLM/prompt-injection text. Never copy the payload into JSON.

Two surfaces in this app:
- what the user types or pastes into the chat composer (scanned here)
- what the browser pane shows the agent in a screenshot (an image, so it cannot
  be regex-scanned; prompts/prompt.md tells the agent to treat on-screen text as
  data, never as instructions)
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLAGS_PATH = HERE / "output" / "prompt_injection_flags.json"

_LOCK = threading.Lock()

# Do not match lone "AI" / "Yale". Instruction-override patterns only.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_previous_instructions", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("ignore_all_instructions", re.compile(r"ignore\s+all\s+instructions", re.I)),
    ("system_prompt", re.compile(r"\bsystem\s+prompt\b", re.I)),
    ("prompt_injection", re.compile(r"prompt\s+inject", re.I)),
    ("jailbreak", re.compile(r"\bjailbreak\b", re.I)),
    ("you_are_the_model", re.compile(r"you\s+are\s+(now\s+)?(chatgpt|gpt-\d|claude|an?\s+llm|an?\s+ai\s+language\s+model)", re.I)),
    ("do_not_tell_user", re.compile(r"do\s+not\s+(tell|inform)\s+the\s+(user|human|student|grader)", re.I)),
    ("im_start", re.compile(r"<\|im_start\|>", re.I)),
    ("developer_message", re.compile(r"\bdeveloper\s+message\b", re.I)),
    ("to_the_llm", re.compile(r"\bto\s+the\s+(llm|language\s+model)\b", re.I)),
    ("to_the_ai_colon", re.compile(r"\bto\s+the\s+ai\s*[:\-]", re.I)),
    ("disregard_guardrails", re.compile(r"disregard\s+(your\s+)?(guardrails|safety|rules)", re.I)),
    ("reveal_instructions", re.compile(r"(reveal|repeat|print|show)\s+(your\s+)?(instructions|prompt)", re.I)),
]


def _split_blocks(text: str) -> list[str]:
    parts = re.split(r"(\n\s*\n)", text)
    return parts if parts != [""] else []


def strip_injections(text: str, *, source: str, channel: str = "file") -> tuple[str, list[dict]]:
    """Return cleaned text and flags. Flags never include the matched payload."""
    if not text:
        return "", []
    flags: list[dict] = []
    kept: list[str] = []
    for block in _split_blocks(text):
        if block.strip() == "" or block.isspace():
            kept.append(block)
            continue
        hit = None
        for name, cre in INJECTION_PATTERNS:
            if cre.search(block):
                hit = name
                break
        if hit:
            flags.append({
                "flagged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source_file": source,
                "channel": channel,
                "pattern": hit,
                "status": "pending_decision",
                "action": "ignored_until_decision",
                "payload": None,
                "note": "Matched text was dropped and is not stored. Ignored until you decide treatment.",
            })
            kept.append("\n[INJECTION_DROPPED]\n")
        else:
            kept.append(block)
    return "".join(kept), flags


def append_flags(flags: list[dict], out_path: Path | None = None) -> None:
    """Accumulate flags across chat turns. Never raises into the caller."""
    if not flags:
        return
    target = out_path or FLAGS_PATH
    try:
        with _LOCK:
            target.parent.mkdir(parents=True, exist_ok=True)
            existing: list[dict] = []
            if target.is_file():
                try:
                    loaded = json.loads(target.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        existing = loaded.get("flags") or []
                except (json.JSONDecodeError, OSError):
                    existing = []
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "rule": (
                    "Ignore AI/LLM prompt injections. Do not write the payload into JSON. "
                    "Status stays pending_decision until a human renders treatment."
                ),
                "flag_count": len(existing) + len(flags),
                "flags": [*existing, *flags],
            }
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"prompt_guard: could not write {target}: {exc}", flush=True)
