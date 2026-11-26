"""The desk's core loop: candidates in, IS/OOS results + verdicts out.

Verdict rules are fixed here BEFORE any run, so a candidate cannot talk
its way into a PASS after the fact:

    PASS  OOS trades >= 8 and OOS sharpe > 0.3 and OOS total return > 0
    FAIL  otherwise

Buy & hold on the same OOS window is printed next to every asset: a PASS
that loses to it after costs still has no reason to exist, and the report
says so.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import desk  # noqa: F401 - wires bt
from desk.strategies import DonchianBreakout, RsiMeanReversion, SmaTrendCross
from bt.broker import Broker, CostModel
from bt.data import load_csv
from bt.engine import Backtest
from bt.stats import summary, trade_stats
from bt.strategies import BuyAndHold

OOS_START = datetime(2024, 1, 1)
TS_FORMAT = "%Y-%m-%dT%H:%M:%S"
CASH = 10_000.0

DATA = Path(__file__).resolve().parent.parent / "data"

ASSETS = {
    "BTC": ("btc_1d.csv", CostModel(commission_bps=12.5, slippage_bps=12.5)),
    "XAUUSD": ("xauusd_1d.csv", CostModel(commission_bps=1.5, slippage_bps=1.5)),
}

# Candidate grid: the three paper-trader families plus nearby variants the
# desk is asked to judge. Each entry is (name, factory).
CANDIDATES = [
    ("donchian trail", lambda: DonchianBreakout()),
    ("donchian 3R", lambda: DonchianBreakout(target_r=3.0)),
    ("donchian 40d 3R", lambda: DonchianBreakout(entry=40, target_r=3.0)),
    ("rsi mean-rev", lambda: RsiMeanReversion()),
    ("sma cross trail", lambda: SmaTrendCross()),
    ("sma cross 3R", lambda: SmaTrendCross(target_r=3.0)),
    ("sma 50/100 trail", lambda: SmaTrendCross(fast=50, slow=100)),
]


def verdict(oos_sharpe: float, oos_ret: float, oos_trades: int) -> str:
    if oos_trades >= 8 and oos_sharpe > 0.3 and oos_ret > 0:
        return "PASS"
    return "FAIL"


def run_one(factory, bars, costs):
    bt = Backtest(factory(), Broker(CASH, costs))
    bt.run(bars)
    s = summary(bt.equity_curve)
    t = trade_stats(bt.broker.fills)
    return {**{f"sharpe": s["sharpe"], "ret": s["total_return"],
               "maxdd": s["max_drawdown"]},
            "trades": t["trades"], "win": t["win_rate"], "pf": t["profit_factor"],
            "bt": bt}


def main() -> list[dict]:
    rows = []
    for asset, (fname, costs) in ASSETS.items():
        bars = load_csv(str(DATA / fname), ts_format=TS_FORMAT)
        is_bars = [b for b in bars if b.ts < OOS_START]
        oos_bars = [b for b in bars if b.ts >= OOS_START]
        bh = run_one(BuyAndHold, oos_bars, costs)
        print(f"== {asset}: {len(is_bars)} IS / {len(oos_bars)} OOS bars "
              f"(OOS {oos_bars[0].ts.date()}..{oos_bars[-1].ts.date()}, "
              f"buy&hold OOS {bh['ret']:+.1%}) ==")
        for name, factory in CANDIDATES:
            is_r = run_one(factory, is_bars, costs)
            oos_r = run_one(factory, oos_bars, costs)
            v = verdict(oos_r["sharpe"], oos_r["ret"], oos_r["trades"])
            row = {"asset": asset, "candidate": name, "verdict": v,
                   "oos_ret": oos_r["ret"], "oos_sharpe": oos_r["sharpe"],
                   "oos_maxdd": oos_r["maxdd"], "oos_trades": oos_r["trades"],
                   "oos_win": oos_r["win"], "oos_pf": oos_r["pf"],
                   "is_sharpe": is_r["sharpe"], "is_ret": is_r["ret"],
                   "bh_oos_ret": bh["ret"],
                   "oos_start": str(oos_bars[0].ts.date()),
                   "oos_end": str(oos_bars[-1].ts.date())}
            rows.append(row)
            print(f"{v}  {name:20s} IS sharpe {is_r['sharpe']:5.2f} | "
                  f"OOS ret {oos_r['ret']:+7.1%} sharpe {oos_r['sharpe']:5.2f} "
                  f"maxDD {oos_r['maxdd']:6.1%} trades {oos_r['trades']:3} PF {oos_r['pf']:5.2f}")
    return rows


if __name__ == "__main__":
    main()
