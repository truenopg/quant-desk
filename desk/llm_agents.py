"""Model-backed roles: the LLM proposes hypotheses and writes critiques;
the pass/fail verdict stays with the deterministic validator (agents.Critic)
and the backtest engine. A model reply that cannot be parsed or falls
outside the declared ranges fails loudly - never silently replaced by RNG.
"""
from __future__ import annotations

import json

from desk.agents import FAMILIES, Critic
from desk.model import extract_json


def _clamp(family: str, params: dict) -> dict:
    spec = FAMILIES[family]
    out = {}
    for key, (lo, hi) in spec["ranges"].items():
        v = params.get(key)
        if isinstance(v, list):
            if len(v) != 1:
                raise ValueError(f"{key}: list value {v!r}")
            v = v[0]
        if v is None:
            out[key] = None
            continue
        if key in spec["int_params"]:
            out[key] = int(max(lo, min(hi, round(float(v)))))
        else:
            lo2 = lo if lo is not None else 0.0
            out[key] = round(max(lo2, min(hi, float(v))), 2)
    if family == "sma" and (out.get("fast") or 0) >= (out.get("slow") or 1):
        out["slow"] = out["fast"] + 30
    if family == "donchian" and (out.get("exit") or 99) >= (out.get("entry") or 0):
        out["exit"] = max(10, out["entry"] - 20)
    return out


class ModelProposer:
    """The model sees the allowed families/ranges, what the registry
    already rejected and why, plus research-window stats, and must answer
    with one JSON hypothesis per call."""

    def __init__(self, model):
        self.model = model

    def propose(self, asset: str, stats_summary: str, reg: dict,
                n: int, start_id: int, seed: int) -> tuple[list[dict], list[str]]:
        rejected = [f"{h['family']}{h['params']}: {h['critic']}"
                    for h in reg["hypotheses"]
                    if h["asset"] == asset and h["status"] == "rejected"][-5:]
        ranges = {fam: spec["ranges"] for fam, spec in FAMILIES.items()}
        prompt = (
            "You are the ideation researcher on a systematic trading desk. "
            f"Asset: {asset}. Research-window stats (daily bars before 2024): "
            f"{stats_summary}\n"
            f"Allowed families and parameter ranges: {json.dumps(ranges)}\n"
            "Recently rejected ideas and why: " + json.dumps(rejected) + "\n"
            "Propose ONE new hypothesis, different from the rejected ones. "
            "Every parameter value must be ONE number inside its range, never "
            "a list or a range. Example of the exact shape expected: "
            '{"family": "donchian", "params": {"entry": 45, "exit": 18, '
            '"target_r": 3.0}, "rationale": "captures medium breakouts"}. '
            "Answer with ONLY one JSON object like that.")
        out, raws, last_err = [], [], None
        attempt = 0
        while len(out) < n and attempt < 3 * n:
            raw = self.model.generate(prompt, seed=seed * 1000 + attempt)
            raws.append(raw)
            attempt += 1
            try:
                h = extract_json(raw)
                fam = h["family"]
                if fam not in FAMILIES:
                    raise ValueError(f"unknown family {fam!r}")
                params = _clamp(fam, h["params"])
                dupe = any(x["asset"] == asset and x["family"] == fam
                           and x["params"] == params for x in
                           list(reg["hypotheses"]) + out)
                if dupe:
                    raise ValueError("duplicate of an existing hypothesis")
                out.append({"id": f"M{start_id + len(out):03d}", "asset": asset,
                            "family": fam, "params": params,
                            "rationale": str(h.get("rationale", ""))[:200],
                            "model_raw": raw.strip()[:400], "seen_before": False})
            except Exception as e:
                last_err = e
        if not out:
            raise RuntimeError(f"model produced no valid hypothesis for {asset}: {last_err}")
        return out, raws


class ModelCritic:
    """The model writes the prose critique from deterministic metrics;
    the verdict comes only from the rule-based Critic."""

    def __init__(self, model):
        self.model = model
        self.rules = Critic()

    def review(self, hyp: dict, sel: dict, reg: dict, seed: int = 0) -> tuple[str, str, str]:
        status, reason = self.rules.review(hyp, sel, reg)
        prompt = (
            "You are the critic on a systematic trading desk. The validator "
            "produced these deterministic metrics on the SELECTION window "
            f"(2024-2025) for {hyp['asset']}: "
            f"return {sel['ret']:+.1%}, sharpe {sel['sharpe']:.2f}, "
            f"trades {sel['trades']}. "
            f"Strategy: {hyp['family']} {hyp['params']}. "
            f"Proposer rationale: {hyp['rationale']}. "
            f"The rule-based verdict is {status.upper()}: {reason}. "
            "Write 2-3 sentences of critique: what could be overfit, what "
            "the trade count implies, what would change your mind. Plain text.")
        note = self.model.generate(prompt, seed=seed, max_new_tokens=150).strip()
        return status, reason, note
