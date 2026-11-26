# quant-desk

Research desk for rule-based trading candidates: propose, backtest,
validate out-of-sample, verdict, report. Reuses the vendored
backtest-engine and the strategy families from paper-trader.

Paper research only. Nothing here trades real money, and a PASS is a
protocol verdict on one historical window - not robustness proof and not
a profitability claim. Some PASS verdicts rest on ~10 trades.

## What it is today (v1)

A deterministic pipeline, not an agent team. Candidates are a fixed grid
in `desk/runner.py`; there is no hypothesis generation yet. The desk is
operated by an agent (me) who picks what to test next - the "agentic"
part lives outside the repo for now. Multi-agent ideation/critique is
the roadmap, not the current state.

## Run it

Install first: see INSTALL.md (Linux / macOS / Windows, ~2.5 GB disk
with the model, no keys, no cost).

    python -m desk.fetch              # BTC dailies (Coinbase), gold dailies (Yahoo GC=F)
    python -m desk.runner             # IS/OOS run with verdicts
    python -m desk.cycle --seed 42    # deterministic cycle + registry
    python -m desk.model_cycle --seed 7   # same cycle with the local model
    python -m desk.report             # runs/<today>/report.md + equity figures
    python -m unittest discover -s tests

## Protocol

- Split: in-sample before 2024-01-01, out-of-sample after.
- Costs: BTC 25 bps/side, gold 3 bps/side. Sizing: 1% risk per trade.
- Verdicts are fixed in `runner.verdict` before any run:
  PASS = OOS trades >= 8, OOS sharpe > 0.3, OOS return > 0.
- Every report compares against buy & hold on the exact same bars
  (alignment covered by tests), including maxDD, calmar and time in
  market - raw return alone is not the comparison that matters.

## Data

- BTC: Coinbase BTC-USD daily candles (public API).
- Gold: Yahoo GC=F front-month futures dailies as a XAUUSD proxy.
  It is NOT spot gold; rolls and sessions differ from spot. Same caveat
  as paper-trader's research protocol.

## First run (2026-11-26)

See `runs/2026-11-26/report.md`. Headline: on raw OOS return nothing
beats buy & hold (BTC +35%, gold +70%), but B&H pays for it with -52%
(BTC) / -33% (gold) drawdowns and 100% exposure, while the Donchian
variants make 10-15% with ~-4% maxDD and ~25% time in market - better
calmar than the benchmark on both assets. Whether that trade-off is
worth anything is a question the desk keeps asking, not answers.

## The desk cycle (v2)

    python -m desk.cycle --seed 42     # one full cycle, transcript -> runs/cycle_<today>.md

Roles, each a small deterministic program in `desk/agents.py`:

- **Proposer** draws strategy variants inside declared parameter ranges
  (seeded RNG: same seed + same registry = same proposals).
- **Validator** runs each idea on the selection window (2024-2025).
- **Critic** rejects with written reasons (too few trades, no edge,
  losing, duplicate in registry). Approval is the exception.
- **Gatekeeper** lets at most the single best approved idea per asset
  touch the holdout (2026+), exactly once, and records the outcome.

Every idea lives in `runs/registry.json`: params, rationale, window
metrics, critic note, status transitions. Splits: research <2024,
selection 2024-25, holdout 2026+. The holdout is not virgin for the
seed families (v1 looked at 2024+); discipline applies from the first
cycle on, and a holdout opened too often stops meaning anything - the
registry keeps count.

First cycle (`runs/cycle_2026-11-26.md`): 12 hypotheses, 7 rejected by
the critic, 1 per asset opened the holdout. BTC H002 (donchian 44/14,
3.47R): holdout +4.4% vs buy&hold -30.2%, but only 3 holdout trades -
anecdote, not proof. Gold H009 similar warning with 1 trade.

## Model-backed cycle (v3)

    python -m desk.model_cycle --seed 7        # real local model, holdout CLOSED by default
    python -m desk.model_cycle --backend ollama  # same, via a local Ollama server

A real model sits in the ideation and critique seats
(Qwen2.5-0.5B-Instruct, runs locally on CPU via transformers - no API
key, no cost; `--backend ollama` uses a local Ollama server instead).
The model proposes hypotheses as strict JSON (parsed, range-checked,
duplicate-checked; a bad reply fails loudly, never silently replaced by
RNG) and writes the prose critique. Validation stays deterministic and
separate: backtests on the selection window, verdicts from the
rule-based critic. Raw model replies are stored per hypothesis in
`runs/registry.json` (`model_raw`).

Reproducible: same seed + same registry = same proposals. First model
cycle: `runs/model_cycle_2026-11-26.md` - 4 model hypotheses, 2 selected
on BTC, both GOLD ideas rejected (too few trades), holdout untouched.

Known quality limits, honestly: a 0.5B local model is a weak analyst.
Rationales are generic and its critiques sometimes misread the metrics
(see M001/M003 in the transcript) - useful as a protocol skeleton and a
diversity source, not as research judgment. Swapping in a stronger
model (bigger local, or a paid API) changes only `desk/model.py`.
