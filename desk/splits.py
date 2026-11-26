"""The desk's three data windows. Holdout is locked behind the gatekeeper.

Honesty note: v1 exploration (2026-11-26) already looked at 2024+ data for
the seed families, so the holdout is NOT virgin for those. The registry
marks hypotheses as exploratory when they descend from that seen work.
Discipline starts here: new hypotheses are judged on research+selection,
and the gatekeeper opens the holdout once per hypothesis.
"""
from datetime import datetime

RESEARCH_END = datetime(2024, 1, 1)    # IS: indicator warmup + sanity
SELECTION_END = datetime(2026, 1, 1)   # proposer/critic compete here
# holdout = SELECTION_END .. today, opened once per approved hypothesis
