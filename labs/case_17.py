"""Toy logistic scoring and cost accounting; no trained or bank model."""
from dataclasses import dataclass
import json
import math
import unittest


@dataclass(frozen=True)
class Features:
    amount_cents: int
    velocity: int
    device_change: bool
    age_seconds: int


def validate_features(features):
    values = (features.amount_cents, features.velocity, features.age_seconds)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("non-negative integer features required")
    if type(features.device_change) is not bool:
        raise ValueError("device_change must be boolean")


def toy_score(features):
    validate_features(features)
    amount = min(features.amount_cents / 100000, 4)
    velocity = min(features.velocity, 10)
    z = -4 + 0.5 * amount + 0.7 * velocity
    z += 1.2 * int(features.device_change)
    return 1 / (1 + math.exp(-z))


def decide(features, allow_below=0.30, block_from=0.85):
    if not 0 <= allow_below < block_from <= 1:
        raise ValueError("invalid thresholds")
    if features is None:
        return "REVIEW_MISSING"
    validate_features(features)
    if features.age_seconds > 60:
        return "REVIEW_STALE"
    probability_like = toy_score(features)
    if probability_like >= block_from:
        return "BLOCK"
    if probability_like >= allow_below:
        return "REVIEW"
    return "ALLOW"


def realized_cost(rows, fp_cents=500, review_cents=100):
    if any(type(x) is not int or x < 0 for x in (fp_cents, review_cents)):
        raise ValueError("costs must be non-negative integer cents")
    totals = {"missed_fraud": 0, "false_positive": 0, "review": 0}
    for action, fraud, amount_cents in rows:
        if type(amount_cents) is not int or amount_cents < 0:
            raise ValueError("amount must be non-negative integer cents")
        if type(fraud) is not bool:
            raise ValueError("fraud label must be boolean")
        if action == "ALLOW" and fraud:
            totals["missed_fraud"] += amount_cents
        elif action == "BLOCK" and not fraud:
            totals["false_positive"] += fp_cents
        elif action in {"REVIEW", "REVIEW_MISSING", "REVIEW_STALE"}:
            totals["review"] += review_cents
        elif action not in {"ALLOW", "BLOCK"}:
            raise ValueError("unknown action")
    totals["total"] = sum(totals.values())
    return totals


class FraudTests(unittest.TestCase):
    def test_low(self):
        self.assertEqual(decide(Features(100, 0, False, 1)), "ALLOW")

    def test_high(self):
        self.assertEqual(decide(Features(400000, 10, True, 1)), "BLOCK")

    def test_middle(self):
        self.assertEqual(decide(Features(100000, 4, True, 1)), "REVIEW")

    def test_missing(self):
        self.assertEqual(decide(None), "REVIEW_MISSING")

    def test_stale(self):
        self.assertEqual(decide(Features(100, 0, False, 61)), "REVIEW_STALE")

    def test_future(self):
        with self.assertRaises(ValueError):
            decide(Features(100, 0, False, -1))

    def test_negative(self):
        with self.assertRaises(ValueError):
            toy_score(Features(-1, 0, False, 1))

    def test_threshold_order(self):
        with self.assertRaises(ValueError):
            decide(None, 0.9, 0.1)

    def test_monotonic_velocity(self):
        low = toy_score(Features(10000, 1, False, 1))
        high = toy_score(Features(10000, 5, False, 1))
        self.assertLess(low, high)

    def test_costs(self):
        costs = realized_cost([("ALLOW", True, 10000),
                               ("BLOCK", False, 10000),
                               ("REVIEW", True, 10000)])
        self.assertEqual(costs["total"], 10600)

    def test_zero_loss_when_correct(self):
        self.assertEqual(realized_cost([("ALLOW", False, 100),
                                        ("BLOCK", True, 100)])["total"], 0)

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            realized_cost([("SKIP", False, 10)])

    def test_nonfinite_features_cannot_allow(self):
        for value in (float("nan"), float("inf"), 1.5, True):
            for feature in (Features(value, 0, False, 1),
                            Features(1, value, False, 1),
                            Features(1, 0, False, value)):
                with self.assertRaises(ValueError):
                    decide(feature)

    def test_device_flag_is_boolean(self):
        with self.assertRaises(ValueError):
            decide(Features(1, 0, "false", 1))

    def test_cost_domains(self):
        for value in (float("nan"), float("inf"), -1, 0.5, True):
            with self.assertRaises(ValueError):
                realized_cost([("ALLOW", True, value)])
            with self.assertRaises(ValueError):
                realized_cost([], fp_cents=value)
        with self.assertRaises(ValueError):
            realized_cost([("ALLOW", "false", 1)])

    def test_unknown_review_action(self):
        with self.assertRaises(ValueError):
            realized_cost([("REVIEW_BOGUS", False, 10)])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FraudTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    rows = [("ALLOW", True, 10000), ("BLOCK", False, 10000),
            ("REVIEW", True, 10000)]
    print(json.dumps({"synthetic_cost_cents": realized_cost(rows),
                      "model": "fixed toy weights; not calibrated"}, indent=2))
    raise SystemExit(not result.wasSuccessful())
