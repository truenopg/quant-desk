"""Hypothesis registry: every idea, its verdicts, its state transitions.

proposed -> selected (critic approved) | rejected (critic, with reason)
selected -> holdout-tested (gatekeeper, exactly once)

JSON on purpose: diffable in git, readable without tooling.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "runs" / "registry.json"


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text())
    return {"hypotheses": []}


def save(reg: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(reg, indent=2, sort_keys=True))


def add(reg: dict, hyp: dict) -> dict:
    hyp = dict(hyp)
    hyp["proposed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    hyp["status"] = "proposed"
    reg["hypotheses"].append(hyp)
    return hyp


def find(reg: dict, hyp_id: str) -> dict | None:
    for h in reg["hypotheses"]:
        if h["id"] == hyp_id:
            return h
    return None
