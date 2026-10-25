"""Independent contact-recovery challenge model; no email or banking calls.
Production requires verified identity, rate limits across accounts/devices,
encrypted persistent storage, delivery events and signed device sessions.
Test code is supplied explicitly; real issuers must generate random secrets.
"""
import hashlib
import hmac
import threading
import unittest


class ContactRecovery:
    def __init__(self, owner):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("nonempty owner identity required")
        self.owner, self.generation = owner, 0
        self.challenge, self.contact = None, None
        self.verified, self.device_authorized = False, False
        self.lock = threading.Lock()

    def change_contact(self, owner, contact, identity_verified=False):
        with self.lock:
            if owner != self.owner or identity_verified is not True:
                raise PermissionError("identity review required")
            if not isinstance(contact, str) or "@" not in contact:
                raise ValueError("contact")
            self.generation += 1
            self.contact, self.challenge = contact, None
            self.verified, self.device_authorized = False, False
            return self.generation

    def issue(self, owner, code, now, ttl):
        if owner != self.owner: raise PermissionError("scope")
        if not isinstance(code, str) or len(code) < 6: raise ValueError("code")
        if any(type(x) is not int or x < 0 for x in (now, ttl)) or ttl == 0:
            raise ValueError("clock")
        with self.lock:
            if not self.contact: raise ValueError("contact first")
            if self.challenge and now < self.challenge[2] + 30:
                raise ValueError("resend cooldown")
            digest = hashlib.sha256(code.encode()).digest()
            self.challenge = [self.generation, digest, now, now + ttl, 0]
            return self.generation

    # BEGIN CORE
    def verify(self, owner, generation, code, now):
        if owner != self.owner:
            raise PermissionError("recovery scope")
        if type(now) is not int or now < 0 or not isinstance(code, str):
            raise ValueError("invalid request")
        with self.lock:
            current = self.challenge
            if current is None:
                raise ValueError("challenge unavailable")
            issued_generation, digest, issued_at, expiry, attempts = current
            if type(generation) is not int or generation != self.generation:
                raise ValueError("obsolete contact generation")
            if generation != issued_generation or not issued_at <= now < expiry:
                raise ValueError("challenge expired or not yet valid")
            if attempts >= 3:
                raise ValueError("attempt budget exhausted")
            current[4] += 1
            candidate = hashlib.sha256(code.encode()).digest()
            if not hmac.compare_digest(candidate, digest):
                raise PermissionError("invalid code")
            self.verified, self.challenge = True, None
            return True
    # END CORE


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.r = ContactRecovery("a")
        self.r.change_contact("a", "new@example.test", True)
        self.r.issue("a", "123456", 100, 60)

    # BEGIN TESTS
    def test_contact_change_invalidates_old_code(self):
        self.r.change_contact("a", "other@example.test", True)
        self.r.issue("a", "654321", 110, 60)
        with self.assertRaises(ValueError):
            self.r.verify("a", 1, "123456", 120)
        self.assertTrue(self.r.verify("a", 2, "654321", 120))

    def test_contact_proof_does_not_authorize_device(self):
        self.assertTrue(self.r.verify("a", 1, "123456", 120))
        self.assertTrue(self.r.verified)
        self.assertFalse(self.r.device_authorized)
    # END TESTS

    def test_expiry_boundary(self):
        with self.assertRaises(ValueError): self.r.verify("a", 1, "123456", 160)
    def test_future_clock(self):
        with self.assertRaises(ValueError): self.r.verify("a", 1, "123456", 99)
    def test_budget_exhaustion(self):
        for _ in range(3):
            with self.assertRaises(PermissionError): self.r.verify("a", 1, "bad", 120)
        with self.assertRaises(ValueError): self.r.verify("a", 1, "123456", 120)
    def test_resend_cooldown(self):
        with self.assertRaises(ValueError): self.r.issue("a", "654321", 110, 60)
    def test_resend_invalidates_previous_code(self):
        self.r.issue("a", "654321", 130, 60)
        with self.assertRaises(PermissionError): self.r.verify("a", 1, "123456", 140)
    def test_replay_rejected(self):
        self.r.verify("a", 1, "123456", 120)
        with self.assertRaises(ValueError): self.r.verify("a", 1, "123456", 121)
    def test_other_owner_rejected(self):
        with self.assertRaises(PermissionError): self.r.verify("b", 1, "123456", 120)
    def test_truthy_identity_rejected(self):
        with self.assertRaises(PermissionError):
            self.r.change_contact("a", "x@y.test", 1)
    def test_nan_time(self):
        with self.assertRaises(ValueError): self.r.verify("a", 1, "123456", float("nan"))
    def test_boolean_generation(self):
        with self.assertRaises(ValueError): self.r.verify("a", True, "123456", 120)

    def test_invalid_owner_rejected_before_state_exists(self):
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner):
                candidate = ContactRecovery.__new__(ContactRecovery)
                with self.assertRaises(ValueError): candidate.__init__(owner)
                self.assertEqual(vars(candidate), {})

    def test_missing_identity_cannot_change_issue_or_verify(self):
        for owner in (None, "", " \t\n"):
            with self.subTest(owner=owner):
                with self.assertRaises(PermissionError):
                    self.r.change_contact(owner, "other@example.test", True)
                with self.assertRaises(PermissionError):
                    self.r.issue(owner, "654321", 140, 60)
                with self.assertRaises(PermissionError):
                    self.r.verify(owner, 1, "123456", 120)
        self.assertEqual(self.r.contact, "new@example.test")
        self.assertTrue(self.r.verify("a", 1, "123456", 120))


if __name__ == '__main__':
    unittest.main()
