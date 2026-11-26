"""Desk cycle with a real local model in the ideation and critique seats.

    python -m desk.model_cycle --seed 7 [--per-asset 3] [--open-holdout]

- Proposals come from the model (desk.llm_agents.ModelProposer), given
  research-window stats and the registry's rejection history.
- Validation is deterministic and separate: backtests on the selection
  window, verdicts from the rule-based Critic.
- The model writes each critique from the metrics (ModelCritic).
- The holdout stays CLOSED unless --open-holdout is passed; it has
  already been swept during v1 exploration and more peeks buy nothing.

Resumable: each finished hypothesis is persisted to runs/_model_cycle.json,
so a re-run continues where a killed run stopped. Delete that file (and
the M*** entries in the registry) to start fresh.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import desk  # noqa: F401
from desk import registry as reg_mod
from desk.agents import FAMILIES
from desk.llm_agents import ModelCritic, ModelProposer
from desk.model import LocalHF, OllamaHTTP
from desk.runner import ASSETS, DATA as DESK_DATA, run_one
from desk.splits import RESEARCH_END, SELECTION_END
from bt.data import load_csv

PARTIAL = DESK_DATA.parent / "runs" / "_model_cycle.json"


def stats_summary(bars) -> str:
    closes = [b.close for b in bars]
    rets = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    up = sum(1 for r in rets if r > 0) / len(rets)
    return (f"{len(bars)} bars, total return {closes[-1] / closes[0] - 1:+.1%}, "
            f"up-day share {up:.0%}, worst day {min(rets):+.1%}, best day {max(rets):+.1%}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--per-asset", type=int, default=3)
    ap.add_argument("--open-holdout", action="store_true")
    ap.add_argument("--backend", choices=["hf", "ollama"], default="hf")
    args = ap.parse_args()

    model = LocalHF() if args.backend == "hf" else OllamaHTTP()
    proposer = ModelProposer(model)
    critic = ModelCritic(model)
    reg = reg_mod.load()

    state = json.loads(PARTIAL.read_text()) if PARTIAL.exists() else \
        {"seed": args.seed, "log": [f"# Model desk cycle {date.today().isoformat()} "
                                    f"seed={args.seed} backend={args.backend}", ""],
         "done": []}
    log = state["log"]

    next_id = 1 + max([int(h["id"][1:]) for h in reg["hypotheses"]
                       if h["id"].startswith("M")] or [0])

    for asset, (fname, costs) in ASSETS.items():
        if asset in state["done"]:
            continue
        bars = load_csv(str(DESK_DATA / fname), ts_format="%Y-%m-%dT%H:%M:%S")
        research = [b for b in bars if b.ts < RESEARCH_END]
        selection = [b for b in bars if RESEARCH_END <= b.ts < SELECTION_END]
        holdout = [b for b in bars if b.ts >= SELECTION_END]
        log.append(f"## {asset}  (research <2024, selection 2024-25, "
                   f"holdout 2026+: {'OPEN' if args.open_holdout else 'CLOSED'})")

        hyps, raws = proposer.propose(asset, stats_summary(research), reg,
                                      args.per_asset, next_id, args.seed)
        next_id += len(hyps)
        approved = []
        for h in hyps:
            make = FAMILIES[h["family"]]["make"]
            sel = run_one(lambda: make(h["params"]), selection, costs)
            h["selection"] = {k: round(v, 4) if isinstance(v, float) else v
                              for k, v in sel.items() if k != "bt"}
            status, reason, note = critic.review(h, sel, reg,
                                                 seed=args.seed + next_id)
            h["status"], h["critic"], h["critic_note"] = status, reason, note
            reg_mod.add(reg, h)
            for k in ("status", "selection", "critic", "critic_note", "model_raw"):
                reg["hypotheses"][-1][k] = h[k]
            mark = "+" if status == "selected" else "-"
            log.append(f"{mark} {h['id']} {h['family']} {h['params']}")
            log.append(f"    rationale: {h['rationale']}")
            log.append(f"    selection: ret {sel['ret']:+.1%} sharpe {sel['sharpe']:.2f} "
                       f"trades {sel['trades']} -> {status.upper()}: {reason}")
            log.append(f"    model critique: {note}")
            if status == "selected":
                approved.append((h, make))
            reg_mod.save(reg)
            PARTIAL.write_text(json.dumps(state))

        if approved and args.open_holdout:
            best, make = max(approved, key=lambda x: x[0]["selection"]["sharpe"])
            from bt.strategies import BuyAndHold
            bh = run_one(BuyAndHold, holdout, costs)
            r = run_one(lambda: make(best["params"]), holdout, costs)
            entry = reg_mod.find(reg, best["id"])
            entry["status"] = "holdout-tested"
            entry["holdout"] = {"ret": round(r["ret"], 4), "sharpe": round(r["sharpe"], 4),
                                "trades": r["trades"], "bh_ret": round(bh["ret"], 4)}
            log.append(f"  GATE: {best['id']} opens the holdout (once). "
                       f"Holdout: ret {r['ret']:+.1%} sharpe {r['sharpe']:.2f} "
                       f"trades {r['trades']} | buy&hold {bh['ret']:+.1%}")
        elif approved:
            log.append("  GATE: approved ideas exist but holdout stays closed "
                       "(already swept in v1; reopening buys nothing).")
        else:
            log.append("  GATE: nothing approved, holdout stays locked.")
        log.append("")
        state["done"].append(asset)
        reg_mod.save(reg)
        PARTIAL.write_text(json.dumps(state))

    reg_mod.save(reg)
    out = DESK_DATA.parent / "runs" / f"model_cycle_{date.today().isoformat()}.md"
    out.write_text("\n".join(log))
    print("\n".join(log))
    print("->", out)
    PARTIAL.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
