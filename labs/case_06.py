"""Modelo de decisão contextual; a prova HMAC é fictícia, não atesta Wi-Fi real."""
import hashlib
import hmac
import json
import unittest


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


class ContextPolicy:
    def __init__(self, key):
        self.key = key
        self.epoch = 1
        self.approved = {"device-demo": {"network-demo"}}

    def issue_demo_proof(self, device, network, now, ttl=30):
        body = dict(device=device, network=network, issued=now,
                    expires=now + ttl, epoch=self.epoch)
        signature = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
        return dict(body=body, signature=signature)

    def decide(self, device, amount_cents, street_limit_cents, proof, now,
               permission=True):
        if type(permission) is not bool:
            raise ValueError("boolean_permission_required")
        if (type(amount_cents) is not int or amount_cents <= 0
                or type(street_limit_cents) is not int or street_limit_cents < 0):
            raise ValueError("invalid_money")
        reason = "context_missing"
        trusted = False
        if not permission:
            reason = "permission_missing"
        elif proof:
            body = proof["body"]
            expected = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
            valid = hmac.compare_digest(expected, proof["signature"])
            valid = valid and body["device"] == device
            valid = valid and body["epoch"] == self.epoch
            valid = valid and body["issued"] <= now < body["expires"]
            valid = valid and body["network"] in self.approved.get(device, set())
            trusted, reason = valid, "verified_context" if valid else "context_invalid"
        # Contexto apenas decide este desafio; não autoriza pagamento.
        challenge = amount_cents > street_limit_cents and not trusted
        return dict(challenge=challenge, context_trusted=trusted, reason=reason,
                    payment_authorized=False)


class Tests(unittest.TestCase):
    def setUp(self):
        self.p = ContextPolicy(b"synthetic-test-key-never-production")
        self.proof = self.p.issue_demo_proof("device-demo", "network-demo", 100)

    def decide(self, **changes):
        args = dict(device="device-demo", amount_cents=2000,
                    street_limit_cents=1000, proof=self.proof, now=110)
        args.update(changes)
        return self.p.decide(**args)

    def test_valid_context_removes_only_this_challenge(self):
        result = self.decide()
        self.assertFalse(result["challenge"])
        self.assertFalse(result["payment_authorized"])

    def test_missing_permission_keeps_conservative_state(self):
        result = self.decide(permission=False)
        self.assertTrue(result["challenge"])
        self.assertEqual(result["reason"], "permission_missing")

    def test_expired_and_future_proofs_are_rejected(self):
        for now in (99, 130, 1000):
            self.assertTrue(self.decide(now=now)["challenge"])

    def test_tampered_signature_is_rejected(self):
        proof = json.loads(json.dumps(self.proof))
        proof["body"]["expires"] = 9999
        self.assertTrue(self.decide(proof=proof)["challenge"])

    def test_proof_is_bound_to_device_and_approved_network(self):
        self.assertTrue(self.decide(device="other")["challenge"])
        other = self.p.issue_demo_proof("device-demo", "same-name-fake", 100)
        self.assertTrue(self.decide(proof=other)["challenge"])

    def test_recovery_invalidates_old_context(self):
        self.p.epoch += 1
        self.assertTrue(self.decide()["challenge"])

    def test_below_limit_is_not_automatic_payment_authorization(self):
        result = self.decide(amount_cents=500, proof=None)
        self.assertFalse(result["challenge"])
        self.assertFalse(result["payment_authorized"])

    def test_permission_requires_an_explicit_boolean(self):
        for permission in ("false", "true", 0, 1, None):
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                self.decide(permission=permission)


if __name__ == "__main__":
    print("LAB SINTÉTICO 06: não detecta redes, fraude ou identidade real.")
    unittest.main(verbosity=2)
