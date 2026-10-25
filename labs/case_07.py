"""Independent MED communication projection, not an implementation of DICT.
Strict contiguous adapter sequence requires retry/reconciliation of gaps.
Production must map official versioned contracts, verify messages, persist
deduplication and confirm financial events. No promise of bank-funded recovery.
"""
import threading
import unittest


class RecoveryTimeline:
    def __init__(self, owner, claimed_cents):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("nonempty owner identity required")
        if type(claimed_cents) is not int or claimed_cents <= 0:
            raise ValueError("positive cents")
        self.owner, self.claimed = owner, claimed_cents
        self.sequence, self.recovered, self.state = 0, 0, "reported"
        self.events = {}
        self.lock = threading.Lock()

    # BEGIN CORE
    def apply(self, event_id, sequence, state, cents=0, trusted=False):
        if trusted is not True:
            raise PermissionError("verified MED adapter required")
        if type(sequence) is not int or sequence <= 0 or not event_id:
            raise ValueError("event identity")
        if type(cents) is not int or cents < 0:
            raise ValueError("integer cents required")
        payload = (sequence, state, cents)
        with self.lock:
            if event_id in self.events:
                if self.events[event_id] != payload:
                    raise ValueError("event conflict")
                return False
            if sequence != self.sequence + 1:
                raise ValueError("sequence gap or obsolete event")
            allowed = {"reported": {"analyzing"},
                       "analyzing": {"partial", "closed"},
                       "partial": {"partial", "closed"}}
            if state not in allowed.get(self.state, set()):
                raise ValueError("state transition")
            if state != "partial" and cents != 0:
                raise ValueError("refund must be explicit")
            if state == "partial" and not 0 < cents <= self.claimed - self.recovered:
                raise ValueError("invalid recovery amount")
            self.recovered += cents
            self.sequence, self.state = sequence, state
            self.events[event_id] = payload
            return True
    # END CORE

    def read(self, owner):
        if owner != self.owner: raise PermissionError("case scope")
        with self.lock:
            return dict(state=self.state, recovered_cents=self.recovered,
                        pending_cents=self.claimed - self.recovered,
                        sequence=self.sequence)


class TimelineTests(unittest.TestCase):
    def setUp(self): self.t = RecoveryTimeline("a", 47855)
    def event(self, key, seq, state, cents=0):
        return self.t.apply(key, seq, state, cents, True)

    # BEGIN TESTS
    def test_partial_refund_replay_never_doubles_money(self):
        self.event("analysis", 1, "analyzing")
        self.event("refund-a", 2, "partial", 20000)
        self.assertFalse(self.event("refund-a", 2, "partial", 20000))
        self.event("refund-b", 3, "partial", 27855)
        self.assertEqual(self.t.read("a")["recovered_cents"], 47855)

    def test_gap_retries_after_missing_event(self):
        with self.assertRaises(ValueError):
            self.event("refund", 2, "partial", 100)
        self.event("analysis", 1, "analyzing")
        self.assertTrue(self.event("refund", 2, "partial", 100))
    # END TESTS

    def test_silence_does_not_close_case(self):
        for _ in range(10): self.t.read("a")
        self.assertEqual(self.t.state, "reported")
    def test_cannot_exceed_claim(self):
        self.event("a", 1, "analyzing")
        with self.assertRaises(ValueError): self.event("b", 2, "partial", 47856)
    def test_close_does_not_imply_refund(self):
        self.event("a", 1, "analyzing"); self.event("b", 2, "closed")
        self.assertEqual(self.t.recovered, 0)
    def test_closed_cannot_reopen_without_new_contract(self):
        self.event("a", 1, "analyzing"); self.event("b", 2, "closed")
        with self.assertRaises(ValueError): self.event("c", 3, "partial", 100)
    def test_conflicting_event(self):
        self.event("a", 1, "analyzing")
        with self.assertRaises(ValueError): self.event("a", 2, "partial", 1)
    def test_boolean_money(self):
        self.event("a", 1, "analyzing")
        with self.assertRaises(ValueError): self.event("b", 2, "partial", True)
    def test_nan_money(self):
        with self.assertRaises(ValueError): self.event("a", 1, "analyzing", float("nan"))
    def test_unknown_owner(self):
        with self.assertRaises(PermissionError): self.t.read("b")
    def test_untrusted_event(self):
        with self.assertRaises(PermissionError): self.t.apply("a", 1, "analyzing", 0, 1)
    def test_zero_refund_not_progress(self):
        self.event("a", 1, "analyzing")
        with self.assertRaises(ValueError): self.event("b", 2, "partial", 0)

    def test_invalid_owner_rejected_before_state_exists(self):
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner):
                candidate = RecoveryTimeline.__new__(RecoveryTimeline)
                with self.assertRaises(ValueError): candidate.__init__(owner, 100)
                self.assertEqual(vars(candidate), {})

    def test_missing_read_identity_cannot_access_case(self):
        for owner in (None, "", " \t\n"):
            with self.subTest(owner=owner), self.assertRaises(PermissionError):
                self.t.read(owner)
        self.assertEqual(self.t.read("a")["recovered_cents"], 0)


if __name__ == '__main__':
    unittest.main()
