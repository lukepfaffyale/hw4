"""Shared test setup: every test writes its audit files to a throwaway folder, so the real
backend/output/audit.jsonl and output/audit_trail.json only ever hold live runs."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit  # noqa: E402


@pytest.fixture(autouse=True)
def _audit_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "TRAIL_PATH", tmp_path / "audit_trail.json")
    yield
