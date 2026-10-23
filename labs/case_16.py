"""Synthetic support routing with event-time windows and abstention."""
from dataclasses import dataclass
import json
import math
import unittest


@dataclass(frozen=True)
class Event:
    id: str
    at: int
    received: int
    intent: str
    weight: int


def evidence(events, now, window=180, max_age=30):
    if any(type(x) is not int for x in (now, window, max_age)):
        raise ValueError("integer synthetic time required")
    if window <= 0 or max_age < 0:
        raise ValueError("invalid time bounds")
    unique = {}
    for event in events:
        if type(event.weight) is not int or event.weight < 0:
            raise ValueError("non-negative integer weight required")
        if type(event.at) is not int or type(event.received) is not int:
            raise ValueError("integer synthetic timestamps required")
        if event.received > now or event.at > now:
            continue
        if not now - window < event.at <= now:
            continue
        if now - event.received > max_age:
            continue
        previous = unique.get(event.id)
        if previous is not None and previous != event:
            raise ValueError("conflicting event")
        unique[event.id] = event
    scores = {}
    for event in unique.values():
        scores[event.intent] = scores.get(event.intent, 0) + event.weight
    return scores


def route(scores, available, urgent=False, threshold=0.75, min_weight=4):
    if type(urgent) is not bool:
        raise ValueError("urgent must be boolean")
    if urgent:
        return {"queue": "human_urgent", "reason": "declared_urgency"}
    validate_ranking(scores, threshold, min_weight)
    total = sum(scores.values())
    if total < min_weight:
        return {"queue": "human_general", "reason": "insufficient"}
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    intent, weight = ranked[0]
    confidence = weight / total
    if confidence < threshold or intent not in available:
        return {"queue": "human_general", "reason": "abstention"}
    return {"queue": intent, "reason": "ranked", "share": confidence}


def validate_ranking(scores, threshold, min_weight):
    if (type(threshold) not in (int, float)
            or not math.isfinite(threshold) or not 0 <= threshold <= 1):
        raise ValueError("invalid threshold")
    if type(min_weight) is not int or min_weight <= 0:
        raise ValueError("positive minimum evidence required")
    if any(type(x) is not int or x < 0 for x in scores.values()):
        raise ValueError("non-negative integer weights required")


class RoutingTests(unittest.TestCase):
    def test_clear(self):
        self.assertEqual(route({"card": 8, "pix": 1}, {"card"})[
            "queue"], "card")

    def test_uncertain(self):
        self.assertEqual(route({"card": 5, "pix": 5}, {"card"})[
            "queue"], "human_general")

    def test_empty(self):
        self.assertEqual(route({}, {"card"})["reason"], "insufficient")

    def test_urgent_overrides_prediction(self):
        self.assertEqual(route({"card": 99}, {"card"}, True)[
            "queue"], "human_urgent")

    def test_unavailable(self):
        self.assertEqual(route({"card": 8}, set())["reason"],
                         "abstention")

    def test_duplicate(self):
        e = Event("a", 99, 99, "pix", 4)
        self.assertEqual(evidence([e, e], 100), {"pix": 4})

    def test_conflict(self):
        with self.assertRaises(ValueError):
            evidence([Event("a", 99, 99, "pix", 4),
                      Event("a", 99, 99, "card", 4)], 100)

    def test_future(self):
        self.assertEqual(evidence([Event("a", 101, 101, "pix", 4)],
                                  100), {})

    def test_old_event_arriving_now(self):
        self.assertEqual(evidence([Event("a", 1, 200, "pix", 4)],
                                  200), {})

    def test_old_receipt(self):
        self.assertEqual(evidence([Event("a", 90, 90, "pix", 4)],
                                  150), {})

    def test_negative_weight(self):
        with self.assertRaises(ValueError):
            evidence([Event("a", 99, 99, "pix", -1)], 100)

    def test_low_support(self):
        self.assertEqual(route({"card": 1}, {"card"})["reason"],
                         "insufficient")

    def test_nonfinite_or_fractional_weights(self):
        for value in (float("nan"), float("inf"), -1, 1.5, True):
            with self.assertRaises(ValueError):
                route({"card": value}, {"card"})
            with self.assertRaises(ValueError):
                evidence([Event("a", 99, 99, "card", value)], 100)

    def test_invalid_policy(self):
        for threshold in (float("nan"), -0.1, 1.1):
            with self.assertRaises(ValueError):
                route({"card": 8}, {"card"}, threshold=threshold)
        with self.assertRaises(ValueError):
            route({}, set(), min_weight=0)
        with self.assertRaises(ValueError):
            route({}, set(), urgent="false")

    def test_invalid_timestamps(self):
        with self.assertRaises(ValueError):
            evidence([Event("a", float("nan"), 99, "card", 4)], 100)
        with self.assertRaises(ValueError):
            evidence([], 100, window=0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RoutingTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"clear": route({"card": 8, "pix": 1}, {"card"}),
                      "uncertain": route({"card": 5, "pix": 5},
                                         {"card", "pix"})}, indent=2))
    raise SystemExit(not result.wasSuccessful())
