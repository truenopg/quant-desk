"""The desk's roles. Deterministic agents: each is a small program with a
narrow job and a written rationale, so every decision is reproducible and
auditable. No LLM calls (no keys, no spend); an LLM proposer can replace
Proposer.brain later without touching the protocol.
"""
from __future__ import annotations

import random

from desk.strategies import DonchianBreakout, RsiMeanReversion, SmaTrendCross

FAMILIES = {
    "donchian": {
        "make": lambda p: DonchianBreakout(entry=p["entry"], exit=p["exit"],
                                           target_r=p["target_r"]),
        "ranges": {"entry": (30, 70), "exit": (10, 25), "target_r": (2.0, 4.0)},
        "int_params": {"entry", "exit"},
    },
    "rsi": {
        "make": lambda p: RsiMeanReversion(rsi_period=p["period"],
                                           rsi_entry=p["rsi_entry"]),
        "ranges": {"period": (2, 5), "rsi_entry": (5.0, 15.0)},
        "int_params": {"period"},
    },
    "sma": {
        "make": lambda p: SmaTrendCross(fast=p["fast"], slow=p["slow"],
                                        target_r=p["target_r"]),
        "ranges": {"fast": (10, 40), "slow": (50, 120), "target_r": (None, 3.0)},
        "int_params": {"fast", "slow"},
    },
}


class Proposer:
    """Mutates the seed families inside declared ranges, seeded RNG."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def propose(self, asset: str, n: int, start_id: int) -> list[dict]:
        out = []
        for i in range(n):
            fam = self.rng.choice(sorted(FAMILIES))
            spec = FAMILIES[fam]
            params = {}
            for k, (lo, hi) in spec["ranges"].items():
                if k in spec["int_params"]:
                    v = self.rng.randint(lo, hi)
                elif lo is None:  # optional float: half the time unset
                    v = self.rng.choice([None, hi])
                else:
                    v = round(self.rng.uniform(lo, hi), 2)
                params[k] = v
            if fam == "donchian" and params["exit"] >= params["entry"]:
                params["exit"] = max(10, params["entry"] - 20)
            if fam == "sma" and params["fast"] >= params["slow"]:
                params["slow"] = params["fast"] + 30
            out.append({"id": f"H{start_id + i:03d}", "asset": asset,
                        "family": fam, "params": params,
                        "rationale": f"{fam} variant, params drawn in declared ranges",
                        "seen_before": False})
        return out


class Critic:
    """Rejects with recorded reasons. Approval is the exception.

    Rules (fixed):
    - selection trades < 8:        'too few trades to say anything'
    - selection sharpe <= 0.2:     'no edge on the selection window'
    - selection return <= 0:       'loses money before costs matter'
    - duplicate (family+params already registered for the asset):
                                   'already in the registry'
    """

    MIN_TRADES = 8
    MIN_SHARPE = 0.2

    def review(self, hyp: dict, selection: dict, registry: dict) -> tuple[str, str]:
        for h in registry["hypotheses"]:
            if (h["asset"] == hyp["asset"] and h["family"] == hyp["family"]
                    and h["params"] == hyp["params"]):
                return "rejected", "already in the registry"
        if selection["trades"] < self.MIN_TRADES:
            return "rejected", "too few trades to say anything"
        if selection["sharpe"] <= self.MIN_SHARPE:
            return "rejected", "no edge on the selection window"
        if selection["ret"] <= 0:
            return "rejected", "loses money before costs matter"
        return "selected", "passes selection floor"
