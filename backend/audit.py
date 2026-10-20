"""Two audit files for the agent, both append-only, neither ever wiped by the app.

1. backend/output/audit.jsonl (Problem 5): one JSON Lines record per harness step (every graph node,
   model parts, tool args, observations, checks, final answer, stop reason). Forensic detail, gitignored.
2. output/audit_trail.json (Problem 12): the compact trail of agent-loop activity the assignment asks
   for: time, event, tool name, short args and results, stop reason. One JSON array, grown in place so
   it stays valid JSON after every write. Committed with the repo.

Rules for both: cleaned text only (never the raw payload of a flagged message), no secrets, no user id,
no name, email addresses redacted, every free-text value truncated.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
AUDIT_PATH = HERE / "output" / "audit.jsonl"
TRAIL_PATH = HERE.parent / "output" / "audit_trail.json"
TRAIL_TEXT_LIMIT = 200
_LOCK = threading.Lock()
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_json_array(path: Path, record: dict[str, Any]) -> None:
    """Add one record to a JSON array file without rewriting the records already in it.

    The file is always a valid JSON array: `[` on the first line, one record per line, `]` at the end.
    Appending seeks to the closing bracket, replaces it with `,<record>]`, and never touches earlier
    bytes. A missing or empty file is started; a file whose tail is damaged (a crash mid-write) keeps
    every record it has and the new record is added on its own line, so nothing is lost."""
    line = json.dumps(record, ensure_ascii=False, default=str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open("r+b") as f:
        f.seek(0, 2)
        size = f.tell()
        if size == 0:
            f.write(f"[\n{line}\n]\n".encode("utf-8"))
            return
        tail_len = min(size, 64)
        f.seek(size - tail_len)
        tail = f.read(tail_len)
        idx = tail.rstrip().rfind(b"]")
        if idx < 0:
            f.write(f"\n{line}\n".encode("utf-8"))
            return
        empty = tail[:idx].rstrip().endswith(b"[")
        f.seek(size - tail_len + idx)
        f.truncate()
        f.write((("" if empty else ",\n") + f"{line}\n]\n").encode("utf-8"))


def redact(text: str) -> str:
    """Email addresses never reach the audit trail, even inside a reply the shopper asked for."""
    return _EMAIL_RE.sub("[email]", text)


def _short(value: Any, limit: int = 400) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        text = json.dumps(value, default=str)
    else:
        text = str(value)
    text = redact(text)
    return text if len(text) <= limit else text[:limit] + "…"


class AuditLogger:
    """One logger per chat turn, tagged with a random run id (never a user id or email)."""

    def __init__(self, run_id: str, path: Path | None = None, trail_path: Path | None = None) -> None:
        self.run_id = run_id
        self.path = path or AUDIT_PATH
        self.trail_path = trail_path or TRAIL_PATH
        self.step = 0

    def trail(self, event: str, **fields: Any) -> None:
        """Problem 12: one compact record in output/audit_trail.json. Events: turn, tool_call,
        tool_result, retry, guard, reply, stop. Text is redacted and cut at TRAIL_TEXT_LIMIT."""
        record: dict[str, Any] = {"ts": _now(), "run_id": self.run_id, "event": event}
        for key, value in fields.items():
            if value is None:
                continue
            if isinstance(value, (bool, int, float)):
                record[key] = value
            elif isinstance(value, list) and all(isinstance(v, (str, int)) for v in value) and len(value) <= 10:
                record[key] = [redact(str(v))[:80] for v in value]
            else:
                record[key] = _short(value, TRAIL_TEXT_LIMIT)
        try:
            with _LOCK:
                append_json_array(self.trail_path, record)
        except OSError:
            pass  # the trail must never break a chat

    def log(
        self,
        kind: str,
        *,
        thought: Any = None,
        tool: str | None = None,
        args: Any = None,
        observation: Any = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.step += 1
        record: dict[str, Any] = {
            "run_id": self.run_id,
            "step": self.step,
            "ts": _now(),
            "kind": kind,
        }
        if thought is not None:
            record["thought"] = _short(thought)
        if tool is not None:
            record["tool"] = tool
        if args is not None:
            record["args"] = _short(args, 300)
        if observation is not None:
            record["observation"] = _short(observation)
        if extra:
            record.update(extra)
        try:
            with _LOCK:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, default=str) + "\n")
        except OSError:
            pass  # the audit trail must never break a chat
