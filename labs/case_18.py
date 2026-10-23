"""Point-in-time feature replay with event and knowledge timestamps."""
from dataclasses import dataclass
import hashlib
import json
import math
import unittest


@dataclass(frozen=True)
class Event:
    id: str
    occurred: int
    known: int
    amount_cents: int


def window_sum(events, at, known_at, seconds=60, available=True):
    validate_window(at, known_at, seconds, available)
    if not available:
        return None
    unique = {}
    for event in events:
        values = (event.occurred, event.known, event.amount_cents)
        if any(type(value) is not int for value in values):
            raise ValueError("integer times and cents required")
        if event.known > known_at or event.occurred > at:
            continue
        if not at - seconds < event.occurred <= at:
            continue
        if event.id in unique and unique[event.id] != event:
            raise ValueError("conflicting event")
        unique[event.id] = event
    return sum(event.amount_cents for event in unique.values())


def validate_window(at, known_at, seconds, available):
    if any(type(value) is not int for value in (at, known_at, seconds)):
        raise ValueError("integer synthetic timestamps required")
    if seconds <= 0 or type(available) is not bool:
        raise ValueError("invalid window or availability")


def validate_comparison(batch, online, tolerance):
    for value in (batch, online, tolerance):
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("finite comparison values required")
    if tolerance is None or tolerance < 0:
        raise ValueError("non-negative tolerance required")


def contract_id(window_seconds=60, missing="null", unit="cents"):
    contract = {"window": window_seconds, "missing": missing,
                "unit": unit, "bound": "(at-window, at]", "version": 1}
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]


def compare(batch, online, batch_contract, online_contract, tolerance=0):
    validate_comparison(batch, online, tolerance)
    if batch_contract != online_contract:
        return "CONTRACT_MISMATCH"
    if batch is None or online is None:
        return "MATCH_MISSING" if batch is online else "MISSING_MISMATCH"
    if abs(batch - online) > tolerance:
        return "VALUE_MISMATCH"
    return "MATCH"


class SkewTests(unittest.TestCase):
    def setUp(self):
        self.events = [Event("a", 50, 50, 100), Event("b", 90, 90, 200)]
        self.contract = contract_id()

    def test_matching(self):
        value = window_sum(self.events, 100, 100)
        self.assertEqual(compare(value, 300, self.contract, self.contract),
                         "MATCH")

    def test_future_occurrence(self):
        rows = self.events + [Event("future", 101, 99, 900)]
        self.assertEqual(window_sum(rows, 100, 100), 300)

    def test_late_knowledge(self):
        rows = self.events + [Event("late", 95, 110, 900)]
        self.assertEqual(window_sum(rows, 100, 100), 300)
        self.assertEqual(window_sum(rows, 100, 120), 1200)

    def test_boundary_open_left(self):
        self.assertEqual(window_sum([Event("a", 40, 40, 10)], 100, 100), 0)

    def test_duplicate(self):
        self.assertEqual(window_sum(self.events * 2, 100, 100), 300)

    def test_conflict(self):
        with self.assertRaises(ValueError):
            window_sum(self.events + [Event("a", 50, 50, 999)], 100, 100)

    def test_missing_is_not_zero(self):
        self.assertEqual(compare(None, 0, self.contract, self.contract),
                         "MISSING_MISMATCH")

    def test_missing_agreement(self):
        self.assertEqual(compare(None, None, self.contract, self.contract),
                         "MATCH_MISSING")

    def test_contract_difference(self):
        self.assertNotEqual(contract_id(60), contract_id(30))
        self.assertEqual(compare(0, 0, contract_id(60), contract_id(30)),
                         "CONTRACT_MISMATCH")

    def test_tolerance(self):
        self.assertEqual(compare(100, 101, self.contract, self.contract, 1),
                         "MATCH")

    def test_unavailable_source(self):
        self.assertIsNone(window_sum([], 100, 100, available=False))

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            window_sum([], 100, 100, seconds=0)

    def test_nonfinite_comparison_cannot_match(self):
        for value in (float("nan"), float("inf"), -float("inf"), True):
            with self.assertRaises(ValueError):
                compare(value, 300, self.contract, self.contract)
            with self.assertRaises(ValueError):
                compare(300, value, self.contract, self.contract)

    def test_invalid_tolerance(self):
        for value in (float("nan"), float("inf"), -1, None, True):
            with self.assertRaises(ValueError):
                compare(1, 1, self.contract, self.contract, value)

    def test_integer_event_contract(self):
        for row in (Event("a", 90, 90, float("nan")),
                    Event("a", 90, 90, 1.5),
                    Event("a", float("nan"), 90, 1),
                    Event("a", 90, True, 1)):
            with self.assertRaises(ValueError):
                window_sum([row], 100, 100)
        with self.assertRaises(ValueError):
            window_sum([], float("nan"), 100)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SkewTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    rows = [Event("a", 90, 90, 200), Event("late", 95, 110, 900)]
    print(json.dumps({"known_at_decision_cents": window_sum(rows, 100, 100),
                      "known_later_cents": window_sum(rows, 100, 120),
                      "contract": contract_id()}, indent=2))
    raise SystemExit(not result.wasSuccessful())
