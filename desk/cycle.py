"""One full desk cycle: propose -> selection -> critique -> holdout gate.

    python -m desk.cycle --seed 42 [--per-asset 6]

The transcript printed is the desk's actual decision log: who proposed
what, what the critic rejected and why, and which hypothesis (if any) the
gatekeeper let touch the holdout. Everything lands in runs/registry.json.
"""
from __future__ import annotations

import argparse
from datetime import date

import desk  # noqa: F401
from desk import registry as reg_mod
from desk.agents import Critic, FAMILIES, Proposer
from desk.runner import ASSETS, CASH, run_one
from desk.splits import RESEARCH_END, SELECTION_END
from bt.data import load_csv
from bt.strategies import BuyAndHold


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-asset", type=int, default=6)
    args = ap.parse_args()

    reg = reg_mod.load()
    critic = Critic()
    proposer = Proposer(args.seed + len(reg["hypotheses"]))
    next_id = len(reg["hypotheses"]) + 1
    log = [f"# Desk cycle {date.today().isoformat()} seed={args.seed}", ""]

    for asset, (fname, costs) in ASSETS.items():
        from desk.runner import DATA as DESK_DATA
        bars = load_csv(str(DESK_DATA / fname), ts_format="%Y-%m-%dT%H:%M:%S")
        research = [b for b in bars if b.ts < RESEARCH_END]
        selection = [b for b in bars if RESEARCH_END <= b.ts < SELECTION_END]
        holdout = [b for b in bars if b.ts >= SELECTION_END]
        log.append(f"## {asset}  (research <2024, selection 2024-25, "
                   f"holdout 2026+: {len(holdout)} bars, locked)")

        hyps = proposer.propose(asset, args.per_asset, next_id)
        next_id += len(hyps)
        approved = []
        for h in hyps:
            make = FAMILIES[h["family"]]["make"]
            sel = run_one(lambda: make(h["params"]), selection, costs)
            h["selection"] = {k: round(v, 4) if isinstance(v, float) else v
                              for k, v in sel.items() if k != "bt"}
            status, reason = critic.review(h, sel, reg)
            h["status"] = status
            h["critic"] = reason
            reg_mod.add(reg, h)  # add() resets status to proposed; restore:
            reg["hypotheses"][-1]["status"] = status
            reg["hypotheses"][-1]["selection"] = h["selection"]
            reg["hypotheses"][-1]["critic"] = reason
            mark = "+" if status == "selected" else "-"
            log.append(f"{mark} {h['id']} {h['family']} {h['params']}")
            log.append(f"    selection: ret {sel['ret']:+.1%} sharpe {sel['sharpe']:.2f} "
                       f"trades {sel['trades']} -> {status.upper()}: {reason}")
            if status == "selected":
                approved.append((h, make))

        # holdout gate: at most the single best selection-sharpe hypothesis
        if approved:
            best, make = max(approved, key=lambda x: x[0]["selection"]["sharpe"])
            bh = run_one(BuyAndHold, holdout, costs)
            r = run_one(lambda: make(best["params"]), holdout, costs)
            entry = reg_mod.find(reg, best["id"])
            entry["status"] = "holdout-tested"
            entry["holdout"] = {"ret": round(r["ret"], 4), "sharpe": round(r["sharpe"], 4),
                                "maxdd": round(r["maxdd"], 4),
                                "calmar": round(r["calmar"], 4),
                                "exposure": round(r["exposure"], 4),
                                "trades": r["trades"],
                                "bh_ret": round(bh["ret"], 4),
                                "bh_calmar": round(bh["calmar"], 4),
                                "bars": len(holdout)}
            log.append(f"  GATE: {best['id']} opens the holdout (once). "
                       f"Holdout: ret {r['ret']:+.1%} sharpe {r['sharpe']:.2f} "
                       f"calmar {r['calmar']:.2f} exposure {r['exposure']:.0%} "
                       f"trades {r['trades']} | buy&hold {bh['ret']:+.1%} calmar {bh['calmar']:.2f}")
        else:
            log.append("  GATE: nothing approved, holdout stays locked.")
        log.append("")

    reg_mod.save(reg)
    out = DESK_DATA.parent / "runs" / f"cycle_{date.today().isoformat()}.md"
    out.write_text("\n".join(log))
    print("\n".join(log))
    print("->", out)


if __name__ == "__main__":
    main()
