"""Independent assisted-device recovery model. No biometric implementation.
An approved evidence decision is injected by a trusted reviewer, not inferred
from a photograph. Production needs actual identity checks, secure evidence,
signed sessions, durable locks and privacy/retention review. No real user data.
"""
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor


class Recovery:
    def __init__(self, owner, device, challenge, expires_at):
        if any(not isinstance(value, str) or not value.strip()
               for value in (owner, device, challenge)):
            raise ValueError("nonempty string identities required")
        if type(expires_at) is not int or expires_at <= 0:
            raise ValueError("expiry")
        self.owner, self.device = owner, device
        self.challenge, self.expires_at = challenge, expires_at
        self.state, self.evidence = "collecting", None
        self.lock = threading.Lock()

    def review(self, evidence_ref, approved=False, trusted=False):
        with self.lock:
            if trusted is not True: raise PermissionError("review authority")
            if self.state != "collecting": raise ValueError("state")
            if not evidence_ref or approved is not True:
                raise ValueError("positive identity decision required")
            self.evidence, self.state = evidence_ref, "approved"

    def revoke(self, owner):
        with self.lock:
            if owner != self.owner: raise PermissionError("owner")
            self.state = "revoked"

    # BEGIN CORE
    def authorize(self, owner, device, challenge, now):
        with self.lock:
            if owner != self.owner or device != self.device:
                raise PermissionError("recovery binding")
            if type(now) is not int or now < 0:
                raise ValueError("invalid clock")
            if now >= self.expires_at:
                raise ValueError("challenge expired")
            if challenge != self.challenge:
                raise PermissionError("challenge mismatch")
            if self.state != "approved" or not self.evidence:
                raise ValueError("review required or challenge consumed")
            self.state = "authorized"
            self.challenge = None
            return {"device": self.device, "authorized": True}
    # END CORE


class RecoveryTests(unittest.TestCase):
    def setUp(self): self.r = Recovery("a", "phone-new", "one-use", 100)
    def approve(self): self.r.review("evidence-ref", True, True)
    def auth(self, **kw):
        args = dict(owner="a", device="phone-new", challenge="one-use", now=50)
        args.update(kw); return self.r.authorize(**args)

    # BEGIN TESTS
    def test_parallel_authorization_consumes_once(self):
        self.approve()
        def attempt(_):
            try:
                return self.auth()["authorized"]
            except (ValueError, PermissionError):
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(attempt, range(4)))
        self.assertEqual(result.count(True), 1)

    def test_camera_problem_is_not_identity_proof(self):
        with self.assertRaises(ValueError):
            self.auth()
        self.assertEqual(self.r.state, "collecting")
    # END TESTS

    def test_exact_expiry_rejected(self):
        self.approve()
        with self.assertRaises(ValueError): self.auth(now=100)
    def test_other_device_rejected(self):
        self.approve()
        with self.assertRaises(PermissionError): self.auth(device="stolen")
    def test_other_owner_rejected(self):
        self.approve()
        with self.assertRaises(PermissionError): self.auth(owner="b")
    def test_revoke_prevents_authorization(self):
        self.approve(); self.r.revoke("a")
        with self.assertRaises(ValueError): self.auth()
    def test_truthy_review_not_trusted(self):
        with self.assertRaises(PermissionError): self.r.review("e", True, 1)
    def test_truthy_approval_rejected(self):
        with self.assertRaises(ValueError): self.r.review("e", "true", True)
    def test_missing_evidence_rejected(self):
        with self.assertRaises(ValueError): self.r.review("", True, True)
    def test_nonfinite_time_rejected(self):
        self.approve()
        with self.assertRaises(ValueError): self.auth(now=float("nan"))
    def test_bad_challenge_preserves_valid_attempt(self):
        self.approve()
        with self.assertRaises(PermissionError): self.auth(challenge="bad")
        self.assertTrue(self.auth()["authorized"])
    def test_duplicate_review_rejected(self):
        self.approve()
        with self.assertRaises(ValueError): self.approve()

    def test_invalid_bindings_rejected_before_state_exists(self):
        for field in ("owner", "device", "challenge"):
            for value in (None, "", " \t\n", 0, True):
                with self.subTest(field=field, value=value):
                    args = dict(owner="a", device="d", challenge="c", expires_at=100)
                    args[field] = value
                    candidate = Recovery.__new__(Recovery)
                    with self.assertRaises(ValueError): candidate.__init__(**args)
                    self.assertEqual(vars(candidate), {})

    def test_missing_authorization_bindings_preserve_challenge(self):
        self.approve()
        for field in ("owner", "device", "challenge"):
            for value in (None, "", " \t\n", 0, True):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(PermissionError): self.auth(**{field: value})
                    self.assertEqual((self.r.state, self.r.challenge),
                                     ("approved", "one-use"))
        self.assertTrue(self.auth()["authorized"])


if __name__ == '__main__':
    unittest.main()
