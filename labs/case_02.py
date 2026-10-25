"""Independent balance freshness model. No ledger writes or real Pix calls.
The lock protects one process only. Production needs durable source versions,
authoritative time, authenticated events and account-scoped APIs. An expired
incident never makes an expired balance authoritative. Values are integer cents.
Incident notices are unversioned here; an old notice can replace a new one.
This does not refresh the balance. Versioned incident events belong in integration.
"""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid integer")


class BalanceView:
    def __init__(self, owner):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("nonempty owner identity required")
        self.owner = owner
        self.snapshot = None
        self.incident_until = 0
        self.lock = threading.Lock()

    def publish(self, version, cents, observed_at, valid_until, trusted=False):
        if trusted is not True: raise PermissionError("source authority")
        for value in (version, cents, observed_at, valid_until): integer(value)
        if version == 0 or valid_until <= observed_at:
            raise ValueError("invalid validity window")
        candidate = (version, cents, observed_at, valid_until)
        with self.lock:
            if self.snapshot and version == self.snapshot[0]:
                if candidate != self.snapshot: raise ValueError("version conflict")
                return False
            if self.snapshot and version < self.snapshot[0]: return False
            if self.snapshot and observed_at < self.snapshot[2]:
                raise ValueError("source clock regressed")
            self.snapshot = candidate
            return True

    def incident(self, until, trusted=False):
        if trusted is not True: raise PermissionError("incident authority")
        integer(until)
        with self.lock: self.incident_until = until

    # BEGIN CORE
    def read(self, owner, now):
        if owner != self.owner:
            raise PermissionError("account scope")
        integer(now)
        with self.lock:
            snapshot = self.snapshot
            active_incident = now < self.incident_until
            if snapshot is None:
                return {"state": "unknown", "balance_cents": None,
                        "incident": active_incident, "may_resend": False}
            version, cents, observed, valid_until = snapshot
            if now < observed:
                return {"state": "unknown", "balance_cents": None,
                        "incident": active_incident, "may_resend": False}
            fresh = now < valid_until
            return {"state": "fresh" if fresh else "stale",
                    "balance_cents": cents, "version": version,
                    "as_of": observed, "incident": active_incident,
                    "may_resend": False}
    # END CORE


class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.view = BalanceView("a")
        self.view.publish(1, 12000, 100, 120, True)

    # BEGIN TESTS
    def test_incident_expiry_does_not_refresh_balance(self):
        self.view.incident(125, True)
        result = self.view.read("a", 130)
        self.assertFalse(result["incident"])
        self.assertEqual(result["state"], "stale")
        self.assertFalse(result["may_resend"])

    def test_concurrent_versions_keep_newest(self):
        def publish(version):
            return self.view.publish(version, version * 100, 110, 140, True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(publish, (5, 2, 4, 3)))
        self.assertEqual(self.view.read("a", 115)["version"], 5)
        self.assertEqual(self.view.read("a", 115)["balance_cents"], 500)
    # END TESTS

    def test_exact_expiry_is_stale(self):
        self.assertEqual(self.view.read("a", 120)["state"], "stale")

    def test_future_snapshot_is_unknown(self):
        self.assertEqual(self.view.read("a", 99)["state"], "unknown")

    def test_scope_checked_without_snapshot(self):
        with self.assertRaises(PermissionError): BalanceView("a").read("b", 1)

    def test_untrusted_source_rejected(self):
        with self.assertRaises(PermissionError): self.view.publish(2, 1, 110, 140, 1)

    def test_invalid_time_rejected(self):
        for value in (True, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError): self.view.read("a", value)

    def test_conflicting_same_version_rejected(self):
        with self.assertRaises(ValueError): self.view.publish(1, 1, 100, 120, True)

    def test_replay_is_harmless(self):
        self.assertFalse(self.view.publish(1, 12000, 100, 120, True))

    def test_clock_regression_rejected(self):
        with self.assertRaises(ValueError): self.view.publish(2, 1, 90, 120, True)

    def test_empty_view_never_claims_zero(self):
        self.assertIsNone(BalanceView("a").read("a", 0)["balance_cents"])

    def test_incident_does_not_change_money(self):
        self.view.incident(200, True)
        self.assertEqual(self.view.read("a", 110)["balance_cents"], 12000)

    def test_invalid_owner_rejected_before_state_exists(self):
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner):
                candidate = BalanceView.__new__(BalanceView)
                with self.assertRaises(ValueError): candidate.__init__(owner)
                self.assertEqual(vars(candidate), {})

    def test_missing_read_identity_cannot_access_balance(self):
        for owner in (None, "", " \t\n"):
            with self.subTest(owner=owner), self.assertRaises(PermissionError):
                self.view.read(owner, 110)
        self.assertEqual(self.view.read("a", 110)["balance_cents"], 12000)


if __name__ == '__main__':
    unittest.main()
