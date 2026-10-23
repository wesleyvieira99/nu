def issue_demo_proof(self, device, network, now, ttl=30):
    body = dict(device=device, network=network, issued=now,
                expires=now + ttl, epoch=self.epoch)
    signature = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
    return dict(body=body, signature=signature)

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