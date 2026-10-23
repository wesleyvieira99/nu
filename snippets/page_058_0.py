# Validação dos limites de autoridade e validade.
def test_restore_requires_two_distinct_reviewers(self):
    verified = self.store.transition("case", 0, "verify", "reviewer-a", 101)
    self.assertEqual(verified["state"], "verified")
    with self.assertRaises(ValueError):
        self.store.transition("case", 1, "restore", "reviewer-a", 102)
    result = self.store.transition("case", 1, "restore", "reviewer-b", 102)
    self.assertEqual((result["state"], result["epoch"]), ("restored", 1))

def test_owner_cannot_verify(self):
    with self.assertRaises(ValueError):
        self.store.transition("case", 0, "verify", "customer", 101)
    self.assertEqual(self.store.read("case")["revision"], 0)

def test_expired_case_cannot_restore(self):
    self.store.transition("case", 0, "verify", "a", 101)
    with self.assertRaisesRegex(ValueError, "expired"):
        self.store.transition("case", 1, "restore", "b", 400)