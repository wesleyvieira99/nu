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