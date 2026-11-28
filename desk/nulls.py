"""Null checks: prove the pipeline reacts when there is nothing to find.

    python -m desk.nulls [--shuffles 20]

1. Shuffled-path null: destroy the serial structure of the real series
   (shuffle daily returns, rebuild a synthetic path with the same return
   distribution) and re-run the v1 grid verdicts. If the desk still
   "finds" edges at the same rate, the verdicts are noise, not signal.
2. Broken-data nulls: a flat series must produce zero trades and no
   PASS; a NaN-corrupted series must fail loudly, not return a number.
"""
from __future__ import annotations

import argparse
import math
import random

import desk  # noqa: F401
from desk.runner import ASSETS, CASH, run_one, verdict
from bt.core import Bar
from bt.data import load_csv
from desk.runner import DATA as DESK_DATA

GRID = None  # filled in main() from runner's own grid


def shuffled(bars, seed):
    """Same returns, same dates, shuffled order: kills trend/mean-reversion."""
    rng = random.Random(seed)
    rets = [bars[i].close / bars[i - 1].close - 1 for i in range(1, len(bars))]
    rng.shuffle(rets)
    out, price = [bars[0]], bars[0].close
    for b, r in zip(bars[1:], rets):
        open_ = price
        close = price * (1 + r)
        span = abs(close - open_)
        out.append(Bar(b.ts, open_, close + span * 0.25,
                       close - span * 0.25, close, b.volume))
        price = close
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shuffles", type=int, default=20)
    args = ap.parse_args()
    from desk.runner import CANDIDATES
    log = ["# Null checks", ""]

    for asset, (fname, costs) in ASSETS.items():
        bars = load_csv(str(DESK_DATA / fname), ts_format="%Y-%m-%dT%H:%M:%S")
        real_pass = 0
        for name, factory in CANDIDATES:
            r = run_one(factory, bars, costs)
            if verdict(r["sharpe"], r["ret"], r["trades"]) == "PASS":
                real_pass += 1
        null_pass = 0
        for s in range(args.shuffles):
            sb = shuffled(bars, seed=1000 + s)
            for name, factory in CANDIDATES:
                r = run_one(factory, sb, costs)
                if verdict(r["sharpe"], r["ret"], r["trades"]) == "PASS":
                    null_pass += 1
        total = args.shuffles * len(CANDIDATES)
        log.append(f"## {asset}: real grid PASS {real_pass}/{len(CANDIDATES)}, "
                   f"shuffled-path PASS {null_pass}/{total} "
                   f"({null_pass / total:.0%} over {args.shuffles} shuffles)")
        log.append("")

    flat = [Bar(b.ts, 100.0, 100.0, 100.0, 100.0, 1.0)
            for b in load_csv(str(DESK_DATA / "btc_1d.csv"),
                              ts_format="%Y-%m-%dT%H:%M:%S")[:300]]
    name, factory = CANDIDATES[0]
    r = run_one(factory, flat, 0.0005)
    v = verdict(r["sharpe"], r["ret"], r["trades"])
    log.append(f"## flat series: {name} -> trades {r['trades']}, "
               f"ret {r['ret']:+.2%}, verdict {v} "
               f"(expected: 0 trades, no PASS)")

    broken = shuffled(flat, seed=7)
    for i in range(50, 60):
        b = broken[i]
        broken[i] = Bar(b.ts, float("nan"), b.high, b.low, b.close, b.volume)
    try:
        r = run_one(factory, broken, 0.0005)
        loud = math.isnan(r["ret"]) or math.isnan(r["sharpe"])
        log.append(f"## NaN-corrupted series: ret {r['ret']}, sharpe {r['sharpe']} "
                   f"-> {'NaN propagates (loud, acceptable)' if loud else 'WARNING: silent number'}")
    except Exception as e:
        log.append(f"## NaN-corrupted series: raised {type(e).__name__} (loud, acceptable)")

    out = DESK_DATA.parent / "runs" / "nulls.md"
    out.write_text("\n".join(log))
    print("\n".join(log))
    print("->", out)


if __name__ == "__main__":
    main()
