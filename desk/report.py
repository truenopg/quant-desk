"""Write runs/<today>/: report.md + OOS equity curves per asset."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from desk.runner import ASSETS, CANDIDATES, OOS_START, CASH, run_one, verdict
from bt.data import load_csv
from bt.strategies import BuyAndHold

RUNS = Path(__file__).resolve().parent.parent / "runs"


def main() -> None:
    out = RUNS / date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# Desk run {date.today().isoformat()}",
             "",
             "Verdict rules (fixed before the run): PASS = OOS trades >= 8,",
             "OOS sharpe > 0.3, OOS return > 0. OOS = from 2024-01-01.",
             "Costs per side: BTC 25 bps, gold 3 bps. 1% risk per trade.",
             "A PASS that trails buy & hold after costs is flagged - the",
             "protocol says such a strategy has no reason to exist.",
             ""]
    for asset, (fname, costs) in ASSETS.items():
        bars = load_csv(str(Path(__file__).resolve().parent.parent / "data" / fname),
                        ts_format="%Y-%m-%dT%H:%M:%S")
        oos = [b for b in bars if b.ts >= OOS_START]
        bh = run_one(BuyAndHold, oos, costs)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ts = [b.ts for b in oos]
        ax.plot(ts, [e / CASH - 1 for e in bh["bt"].equity_curve],
                color="black", lw=1.2, label="buy & hold")
        lines += [f"## {asset} (OOS {oos[0].ts.date()} .. {oos[-1].ts.date()}, "
                  f"buy&hold {bh['ret']:+.1%})", "",
                  "| candidate | verdict | OOS ret | sharpe | maxDD | calmar | exposure | trades |",
                  "|---|---|---|---|---|---|---|---|",
                  f"| **buy & hold** | - | {bh['ret']:+.1%} | - | {bh['maxdd']:.1%} | {bh['calmar']:.2f} | 100% | - |"]
        for name, factory in CANDIDATES:
            r = run_one(factory, oos, costs)
            v = verdict(r["sharpe"], r["ret"], r["trades"])
            lines.append(f"| {name} | {v} | {r['ret']:+.1%} | {r['sharpe']:.2f} | "
                         f"{r['maxdd']:.1%} | {r['calmar']:.2f} | {r['exposure']:.0%} | {r['trades']} |")
            if v == "PASS":
                ax.plot(ts, [e / CASH - 1 for e in r["bt"].equity_curve],
                        lw=1, label=name)
        ax.axhline(0, color="gray", lw=0.5)
        ax.set_title(f"{asset} OOS equity vs buy & hold (PASS candidates only)")
        ax.legend(fontsize=8)
        ax.yaxis.set_major_formatter(lambda x, _: f"{x:+.0%}")
        fig.tight_layout()
        fig.savefig(out / f"oos_equity_{asset.lower()}.png", dpi=110)
        plt.close(fig)
        lines.append(f"![{asset} OOS](oos_equity_{asset.lower()}.png)")
        lines.append("")
    (out / "report.md").write_text("\n".join(lines))
    print("->", out / "report.md")


if __name__ == "__main__":
    main()
