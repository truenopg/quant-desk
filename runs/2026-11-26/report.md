# Desk run 2026-11-26

Verdict rules (fixed before the run): PASS = OOS trades >= 8,
OOS sharpe > 0.3, OOS return > 0. OOS = from 2024-01-01.
Costs per side: BTC 25 bps, gold 3 bps. 1% risk per trade.
A PASS that trails buy & hold after costs is flagged - the
protocol says such a strategy has no reason to exist.

## BTC (OOS 2024-01-01 .. 2026-11-26, buy&hold +35.3%)

| candidate | verdict | OOS ret | sharpe | maxDD | calmar | exposure | trades |
|---|---|---|---|---|---|---|---|
| **buy & hold** | - | +35.3% | - | -52.1% | 0.14 | 100% | - |
| donchian trail | PASS | +10.5% | 0.61 | -5.0% | 0.48 | 36% | 10 |
| donchian 3R | PASS | +11.9% | 0.93 | -4.2% | 0.64 | 24% | 13 |
| donchian 40d 3R | PASS | +15.3% | 1.09 | -4.6% | 0.75 | 23% | 15 |
| rsi mean-rev | FAIL | +3.8% | 0.88 | -0.9% | 1.01 | 2% | 6 |
| sma cross trail | FAIL | +0.3% | 0.04 | -4.1% | 0.02 | 25% | 10 |
| sma cross 3R | FAIL | +6.0% | 0.65 | -3.0% | 0.46 | 22% | 6 |
| sma 50/100 trail | FAIL | +4.1% | 0.26 | -5.0% | 0.19 | 33% | 5 |
![BTC OOS](oos_equity_btc.png)

## GOLD (OOS 2024-01-02 .. 2026-11-26, buy&hold +69.9%)

| candidate | verdict | OOS ret | sharpe | maxDD | calmar | exposure | trades |
|---|---|---|---|---|---|---|---|
| **buy & hold** | - | +69.9% | - | -33.2% | 0.60 | 100% | - |
| donchian trail | FAIL | +16.2% | 0.77 | -8.3% | 0.64 | 39% | 6 |
| donchian 3R | PASS | +14.0% | 1.35 | -2.6% | 1.80 | 23% | 13 |
| donchian 40d 3R | PASS | +15.4% | 1.43 | -2.5% | 2.03 | 26% | 13 |
| rsi mean-rev | FAIL | +0.8% | 0.27 | -1.4% | 0.21 | 4% | 7 |
| sma cross trail | FAIL | +19.7% | 0.97 | -7.4% | 0.86 | 46% | 2 |
| sma cross 3R | FAIL | +9.6% | 1.76 | -1.2% | 2.67 | 13% | 3 |
| sma 50/100 trail | FAIL | +2.7% | 0.89 | -0.8% | 1.24 | 2% | 0 |
![GOLD OOS](oos_equity_gold.png)
