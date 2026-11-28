# Demo notes (2026-11-29)

What this repo is: a small systematic-strategy desk. Strategies are
proposed, validated on a fixed selection window, critiqued with written
reasons, and only then may touch a locked holdout - once. A local model
(Qwen2.5-0.5B, CPU, no keys, no cost) sits in the ideation and critique
seats; every verdict stays deterministic.

Show, in this order:

1. `python -m desk.fetch` - free public data, BTC + gold dailies.
2. `python -m desk.model_cycle --seed 7` - watch the model propose,
   the validator backtest, the critic reject with reasons
   (transcript: runs/model_cycle_2026-11-26.md).
3. `cat runs/registry.json` - every hypothesis, its metrics, the raw
   model reply, and any parameter normalization recorded.
4. `python -m desk.nulls` - shuffled-price nulls and broken-data checks:
   flat series -> 0 trades, NaN -> loud error.
5. `python -m unittest discover -s tests` - 8 tests.

Honest limits to say out loud: the 0.5B model is a weak analyst
(generic rationales, occasional misread of metrics); selection-window
PASS with ~8-10 trades is a filter, not proof; the holdout is not
virgin for the v1 seed families; nothing here claims profitability.
