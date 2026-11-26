# quant-desk

A small research desk for trading rule candidates: propose, backtest,
validate out-of-sample, verdict, report. Reuses the vendored
backtest-engine and the strategy families from paper-trader.

Paper research only. Nothing here trades real money and a PASS is a
protocol verdict, not a profitability claim.

## The loop

    python -m desk.fetch            # refresh BTC (Coinbase) + gold (Yahoo) dailies
    python -m desk.runner           # IS/OOS run, verdicts printed
    python -m desk.report           # runs/<today>/report.md + equity figures

- Candidates live in `desk/runner.py` (name -> factory). Adding a variant
  is one line.
- Split: in-sample before 2024-01-01, out-of-sample after.
- Costs: BTC 25 bps/side, gold 3 bps/side. Sizing: 1% risk per trade.
- Verdicts are fixed in `runner.verdict` before any run:
  PASS = OOS trades >= 8, OOS sharpe > 0.3, OOS return > 0.
- Every report prints buy & hold on the same window; a PASS trailing it
  after costs is flagged as having no reason to exist.

## First run (2026-11-26)

See `runs/2026-11-26/report.md`. Headline: the Donchian family passes its
own rules on both assets with small drawdowns, but nothing beats simple
buy & hold OOS on raw return - BTC +35%, gold +70% over the window. The
desk's job is exactly to keep that comparison in front of every idea.
