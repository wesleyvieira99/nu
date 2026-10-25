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