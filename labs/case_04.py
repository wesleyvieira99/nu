"""Agregação sintética: incompleto não significa zero. Sem Open Finance real."""
from dataclasses import dataclass
import unittest


@dataclass(frozen=True)
class Resource:
    status: str
    cents: int | None
    sequence: int
    observed_at: int
    consent_epoch: int


class Portfolio:
    def __init__(self, required):
        self.required = frozenset(required)
        self.resources = {}
        self.consent_epoch = 1
        self.active = True

    def apply(self, key, resource):
        if not self.active or resource.consent_epoch != self.consent_epoch:
            return False
        if type(resource.sequence) is not int or resource.sequence < 0:
            raise ValueError("integer_sequence_required")
        if key not in self.required:
            raise ValueError("unknown_resource")
        if resource.status not in ("complete", "unsupported", "unavailable"):
            raise ValueError("status")
        if resource.status == "complete":
            if type(resource.cents) is not int or resource.cents < 0:
                raise ValueError("amount")
        elif resource.cents is not None:
            raise ValueError("unknown_is_not_zero")
        old = self.resources.get(key)
        if old and resource.sequence <= old.sequence:
            return False
        self.resources[key] = resource
        return True

    def revoke(self):
        self.active = False
        self.consent_epoch += 1
        self.resources.clear()

    def summarize(self, now, max_age=60):
        total, gaps = 0, {}
        if not self.active:
            return dict(cents=None, complete=False, gaps={"consent": "revoked"})
        for key in sorted(self.required):
            item = self.resources.get(key)
            if item is None:
                gaps[key] = "missing"
            elif item.status != "complete":
                gaps[key] = item.status
            elif not 0 <= now - item.observed_at <= max_age:
                gaps[key] = "stale_or_future"
            else:
                total += item.cents
        return dict(cents=total, complete=not gaps, gaps=gaps)


class Tests(unittest.TestCase):
    def setUp(self):
        self.p = Portfolio(("account", "investment"))

    def resource(self, cents=100, **changes):
        args = dict(status="complete", cents=cents, sequence=1,
                    observed_at=100, consent_epoch=1)
        args.update(changes)
        return Resource(**args)

    def test_partial_is_not_complete(self):
        self.p.apply("account", self.resource())
        self.assertEqual(self.p.summarize(110),
                         dict(cents=100, complete=False, gaps={"investment": "missing"}))

    def test_zero_is_a_real_complete_position(self):
        self.p.apply("account", self.resource())
        self.p.apply("investment", self.resource(0))
        self.assertTrue(self.p.summarize(110)["complete"])

    def test_unsupported_requires_none(self):
        with self.assertRaises(ValueError):
            self.p.apply("investment", self.resource(0, status="unsupported"))
        self.p.apply("investment", self.resource(None, status="unsupported"))
        self.assertEqual(self.p.summarize(110)["gaps"]["investment"], "unsupported")

    def test_old_or_duplicate_events_do_not_overwrite(self):
        self.p.apply("account", self.resource(200, sequence=2))
        self.assertFalse(self.p.apply("account", self.resource(100)))
        self.assertFalse(self.p.apply("account", self.resource(300, sequence=2)))
        self.assertEqual(self.p.summarize(110)["cents"], 200)

    def test_stale_position_is_excluded_and_flagged(self):
        self.p.apply("account", self.resource())
        summary = self.p.summarize(200)
        self.assertEqual(summary["cents"], 0)
        self.assertEqual(summary["gaps"]["account"], "stale_or_future")

    def test_revocation_fences_inflight_events(self):
        self.p.apply("account", self.resource())
        self.p.revoke()
        self.assertFalse(self.p.apply("investment", self.resource()))
        self.assertIsNone(self.p.summarize(110)["cents"])
        self.assertFalse(self.p.resources)

    def test_future_observation_is_not_trusted(self):
        self.p.apply("account", self.resource(observed_at=999))
        self.assertFalse(self.p.summarize(100)["complete"])

    def test_invalid_sequence_cannot_overwrite_newer_resource(self):
        self.p.apply("account", self.resource(200, sequence=2))
        for sequence in (float("nan"), float("inf"), 1.0, True, -1):
            with self.subTest(sequence=sequence), self.assertRaises(ValueError):
                self.p.apply("account", self.resource(999, sequence=sequence))
        self.assertEqual(self.p.resources["account"].sequence, 2)
        self.assertEqual(self.p.summarize(110)["cents"], 200)


if __name__ == "__main__":
    print("LAB SINTÉTICO 04: contratos propostos, sem conexão bancária.")
    unittest.main(verbosity=2)
