import unittest
from datetime import datetime

from desk.runner import verdict, exposure, run_one, ASSETS, CASH
from desk import runner
from bt.core import Fill, Side
from bt.data import load_csv
from bt.strategies import BuyAndHold


class TestVerdict(unittest.TestCase):
    def test_pass_needs_all_three(self):
        self.assertEqual(verdict(0.5, 0.1, 10), "PASS")
        self.assertEqual(verdict(0.5, 0.1, 7), "FAIL")   # too few trades
        self.assertEqual(verdict(0.2, 0.1, 10), "FAIL")  # weak sharpe
        self.assertEqual(verdict(0.5, -0.1, 10), "FAIL") # losing


def _fill(day, side, qty=1.0):
    return Fill(ts=datetime(2026, 1, day), side=side, qty=qty,
                price=100.0, commission=0.0)


class _Bar:
    def __init__(self, day):
        self.ts = datetime(2026, 1, day)
        self.close = 100.0


class TestExposure(unittest.TestCase):
    def test_flat_is_zero(self):
        self.assertEqual(exposure([], [_Bar(d) for d in range(1, 11)]), 0.0)

    def test_half_the_bars(self):
        bars = [_Bar(d) for d in range(1, 11)]
        fills = [_fill(1, Side.BUY), _fill(6, Side.SELL)]
        self.assertAlmostEqual(exposure(fills, bars), 0.5)


class TestBenchmarkAlignment(unittest.TestCase):
    """Strategy and buy&hold results must cover the exact same bars."""

    def test_same_window(self):
        path, costs = ASSETS["BTC"]
        bars = load_csv(str(runner.DATA / path), ts_format=runner.TS_FORMAT)
        oos = [b for b in bars if b.ts >= runner.OOS_START]
        bh = run_one(BuyAndHold, oos, costs)
        self.assertEqual(len(bh["bt"].equity_curve), len(oos))
        # engine fills at the NEXT bar's open, so B&H is flat for bar 1 only
        self.assertAlmostEqual(bh["exposure"], 1 - 1 / len(oos), places=6)
        from desk.strategies import DonchianBreakout
        r = run_one(lambda: DonchianBreakout(target_r=3.0), oos, costs)
        self.assertEqual(len(r["bt"].equity_curve), len(oos))


if __name__ == "__main__":
    unittest.main()

import unittest as _u
from desk.model import extract_json
from desk.llm_agents import _clamp


class TestModelParsing(_u.TestCase):
    def test_extract_json_from_prose(self):
        h = extract_json('Sure! ```json\n{"family": "rsi", "params": {"period": 2, "rsi_entry": 9.5}}\n``` ok')
        self.assertEqual(h["family"], "rsi")
        self.assertEqual(h["params"]["period"], 2)

    def test_extract_json_fails_loud(self):
        with self.assertRaises(ValueError):
            extract_json("no json here")

    def test_clamp_unwraps_and_bounds(self):
        p = _clamp("donchian", {"entry": [45], "exit": 99, "target_r": 9.9})
        self.assertEqual(p, {"entry": 45, "exit": 25, "target_r": 4.0})
        p = _clamp("sma", {"fast": 40, "slow": 30, "target_r": None})
        self.assertGreater(p["slow"], p["fast"])
        self.assertIsNone(p["target_r"])
