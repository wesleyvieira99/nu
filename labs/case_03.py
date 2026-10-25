"""Independent restriction review model, not legal advice or banking software.
Roles/verified flags are test boundaries; production needs authenticated roles,
case-specific legal rules, durable transactions and independent reconciliation.
Review dates trigger work, never automatic fund release. One-process lock only.
"""
import threading
import unittest


class Restriction:
    def __init__(self, owner, cents, review_at):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("nonempty owner identity required")
        if type(cents) is not int or cents <= 0:
            raise ValueError("positive integer cents")
        if type(review_at) is not int or review_at < 0:
            raise ValueError("review time")
        self.owner, self.cents, self.review_at = owner, cents, review_at
        self.version, self.state, self.reason = 1, "restricted", None
        self.released = 0
        self.lock = threading.Lock()

    def due(self, now):
        if type(now) is not int or now < 0: raise ValueError("time")
        return self.state == "restricted" and now >= self.review_at

    def decide(self, expected, role, evidence_ref, release_eligible=False):
        with self.lock:
            if role != "reviewer": raise PermissionError("review scope")
            if type(expected) is not int or expected != self.version:
                raise ValueError("stale decision")
            if not evidence_ref or release_eligible is not True:
                raise ValueError("documented eligibility required")
            if self.state != "restricted": raise ValueError("state")
            self.reason, self.state = evidence_ref, "exit_approved"
            self.version += 1

    # BEGIN CORE
    def execute_exit(self, expected, role, destination_owner,
                     reconciled_cents, no_active_hold=False):
        with self.lock:
            if role != "executor":
                raise PermissionError("execution scope")
            if type(expected) is not int or expected != self.version:
                raise ValueError("stale execution")
            if self.state != "exit_approved":
                raise ValueError("review required")
            if (not isinstance(destination_owner, str)
                    or not destination_owner.strip()
                    or destination_owner != self.owner):
                raise PermissionError("destination ownership")
            if type(reconciled_cents) is not int:
                raise ValueError("integer cents required")
            if reconciled_cents != self.cents:
                raise ValueError("reconcile before transfer")
            if no_active_hold is not True:
                raise ValueError("legal and risk holds unresolved")
            self.state = "transferred"
            self.released = self.cents
            self.version += 1
            return self.released
    # END CORE


class RestrictionTests(unittest.TestCase):
    def setUp(self): self.case = Restriction("company", 200000100, 10)
    def approve(self): self.case.decide(1, "reviewer", "review-1", True)
    def execute(self, **kw):
        args = dict(expected=2, role="executor", destination_owner="company",
                    reconciled_cents=200000100, no_active_hold=True)
        args.update(kw); return self.case.execute_exit(**args)

    # BEGIN TESTS
    def test_overdue_review_does_not_release_money(self):
        self.assertTrue(self.case.due(999))
        self.assertEqual(self.case.state, "restricted")
        self.assertEqual(self.case.released, 0)

    def test_reconciliation_failure_preserves_approval(self):
        self.approve()
        with self.assertRaises(ValueError):
            self.execute(reconciled_cents=1)
        self.assertEqual(self.case.state, "exit_approved")
        self.assertEqual(self.case.released, 0)
        self.assertEqual(self.execute(), 200000100)
    # END TESTS

    def test_review_role_cannot_execute(self):
        self.approve()
        with self.assertRaises(PermissionError): self.execute(role="reviewer")
    def test_owner_mismatch(self):
        self.approve()
        with self.assertRaises(PermissionError): self.execute(destination_owner="x")
    def test_active_hold_blocks(self):
        self.approve()
        with self.assertRaises(ValueError): self.execute(no_active_hold=False)
    def test_truthy_hold_clearance_is_rejected(self):
        self.approve()
        with self.assertRaises(ValueError): self.execute(no_active_hold="yes")
    def test_repeat_cannot_transfer_twice(self):
        self.approve(); self.execute()
        with self.assertRaises(ValueError): self.execute(expected=3)
        self.assertEqual(self.case.released, 200000100)
    def test_stale_review_rejected(self):
        with self.assertRaises(ValueError): self.case.decide(0, "reviewer", "r", True)
    def test_evidence_required(self):
        with self.assertRaises(ValueError): self.case.decide(1, "reviewer", "", True)
    def test_timer_nan_rejected(self):
        with self.assertRaises(ValueError): self.case.due(float("nan"))
    def test_review_is_not_release(self):
        self.approve(); self.assertEqual(self.case.released, 0)
    def test_invalid_amount(self):
        with self.assertRaises(ValueError): Restriction("x", True, 1)

    def test_invalid_owner_rejected_before_state_exists(self):
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner):
                candidate = Restriction.__new__(Restriction)
                with self.assertRaises(ValueError): candidate.__init__(owner, 100, 1)
                self.assertEqual(vars(candidate), {})

    def test_missing_destination_identity_never_releases_money(self):
        self.approve()
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner), self.assertRaises(PermissionError):
                self.execute(destination_owner=owner)
            self.assertEqual((self.case.state, self.case.released, self.case.version),
                             ("exit_approved", 0, 2))


if __name__ == '__main__':
    unittest.main()
