"""Independent synthetic release gate. No mobile SDK or production data."""
from dataclasses import dataclass
import json
import math
import unittest


@dataclass(frozen=True)
class Attempt:
    session: str
    cohort: str
    version: str
    completed: bool
    latency_ms: int


def summarize(attempts):
    unique = {}
    for row in attempts:
        if type(row.latency_ms) is not int or row.latency_ms < 0:
            raise ValueError("latency must be non-negative integer ms")
        if type(row.completed) is not bool:
            raise ValueError("completed must be boolean")
        key = (row.session, row.cohort, row.version)
        previous = unique.get(key)
        if previous is not None and previous != row:
            raise ValueError("conflicting terminal event")
        unique[key] = row
    rows = list(unique.values())
    if not rows:
        return {"n": 0, "rate": None, "p95": None}
    delays = sorted(row.latency_ms for row in rows)
    rank = max(0, (95 * len(delays) + 99) // 100 - 1)
    return {"n": len(rows),
            "rate": sum(row.completed for row in rows) / len(rows),
            "p95": delays[rank]}


def validate_stats(stats):
    if type(stats["n"]) is not int or stats["n"] < 0:
        raise ValueError("invalid sample size")
    if stats["n"] == 0:
        if stats["rate"] is not None or stats["p95"] is not None:
            raise ValueError("empty sample must have absent metrics")
        return
    for name in ("rate", "p95"):
        value = stats[name]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("metrics must be finite numbers")
    if not 0 <= stats["rate"] <= 1 or stats["p95"] < 0:
        raise ValueError("metrics outside domain")


def gate(baseline, candidate, telemetry_complete=True, min_n=50):
    if type(min_n) is not int or min_n <= 0:
        raise ValueError("min_n must be positive integer")
    if type(telemetry_complete) is not bool:
        raise ValueError("telemetry_complete must be boolean")
    validate_stats(baseline)
    validate_stats(candidate)
    if not telemetry_complete:
        return "HOLD_TELEMETRY"
    if baseline["n"] < min_n or candidate["n"] < min_n:
        return "HOLD_SAMPLE"
    if candidate["rate"] < baseline["rate"] - 0.03:
        return "PAUSE_SUCCESS"
    if candidate["p95"] > baseline["p95"] * 1.25:
        return "PAUSE_LATENCY"
    return "ELIGIBLE_FOR_REVIEW"


def fixture(version, successes=98, latency=300):
    return [Attempt(str(i), "wifi-mid", version,
                    i < successes, latency) for i in range(100)]


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.base = summarize(fixture("stable"))

    def test_healthy(self):
        self.assertEqual(gate(self.base, self.base),
                         "ELIGIBLE_FOR_REVIEW")

    def test_success_regression(self):
        bad = summarize(fixture("next", successes=90))
        self.assertEqual(gate(self.base, bad), "PAUSE_SUCCESS")

    def test_tail_regression(self):
        bad = summarize(fixture("next", latency=500))
        self.assertEqual(gate(self.base, bad), "PAUSE_LATENCY")

    def test_missing_telemetry(self):
        self.assertEqual(gate(self.base, self.base, False),
                         "HOLD_TELEMETRY")

    def test_small_sample(self):
        tiny = summarize(fixture("next")[:10])
        self.assertEqual(gate(self.base, tiny), "HOLD_SAMPLE")

    def test_empty(self):
        self.assertIsNone(summarize([])["rate"])

    def test_duplicate(self):
        rows = fixture("next")
        self.assertEqual(summarize(rows + rows), summarize(rows))

    def test_conflict(self):
        rows = fixture("next")
        rows.append(Attempt("0", "wifi-mid", "next", False, 300))
        with self.assertRaises(ValueError):
            summarize(rows)

    def test_negative_latency(self):
        with self.assertRaises(ValueError):
            summarize([Attempt("x", "a", "v", True, -1)])

    def test_nearest_rank(self):
        rows = [Attempt(str(i), "a", "v", True, i)
                for i in range(1, 101)]
        self.assertEqual(summarize(rows)["p95"], 95)

    def test_exact_boundary(self):
        next_stats = dict(self.base, rate=0.95, p95=375)
        self.assertEqual(gate(self.base, next_stats),
                         "ELIGIBLE_FOR_REVIEW")

    def test_versions_are_distinct(self):
        rows = fixture("a") + fixture("b")
        self.assertEqual(summarize(rows)["n"], 200)

    def test_nonfinite_stats_fail_closed(self):
        for name in ("rate", "p95"):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        gate(self.base, dict(self.base, **{name: value}))

    def test_invalid_raw_types(self):
        for done, delay in (("false", 2), (1, 2),
                            (True, float("nan")), (True, True)):
            with self.assertRaises(ValueError):
                summarize([Attempt("a", "b", "v", done, delay)])

    def test_invalid_sample_and_policy(self):
        for stats in (dict(self.base, n=-1), dict(self.base, rate=1.1),
                      dict(self.base, p95=-1), dict(self.base, n=True)):
            with self.assertRaises(ValueError):
                gate(self.base, stats)
        with self.assertRaises(ValueError):
            gate(self.base, self.base, min_n=0)
        with self.assertRaises(ValueError):
            gate(self.base, self.base, telemetry_complete="false")

    def test_empty_sample_holds(self):
        self.assertEqual(gate(self.base, summarize([])), "HOLD_SAMPLE")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReleaseTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    base = summarize(fixture("stable"))
    print(json.dumps({"baseline": base,
                      "healthy": gate(base, base),
                      "regression": gate(base, summarize(
                          fixture("next", successes=90)))}, indent=2))
    raise SystemExit(not result.wasSuccessful())
