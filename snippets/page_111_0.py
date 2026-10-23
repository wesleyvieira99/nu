def test_valid_context_removes_only_this_challenge(self):
    result = self.decide()
    self.assertFalse(result["challenge"])
    self.assertFalse(result["payment_authorized"])

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