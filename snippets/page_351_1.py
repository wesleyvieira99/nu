    def test_unsupported_transfer_never_debits(self):
        q = FXQuote('no', 'owner', 'external_transfer', 'EUR', 'IE',
                    10_000, 1500, 1, 200)
        with self.assertRaises(ValueError):
            self.w.issue(q, 'pricing')
        self.assertEqual(self.w.balance, 100_000)
        self.assertNotIn('no', self.w.quotes)

    def test_capability_change_invalidates_old_preview(self):
        self.w.update_capabilities(set(), 'product-policy')
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'a', 100)
        self.assertEqual(self.w.foreign, {})

    def test_expiry_does_not_trigger_reverse_conversion(self):
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'a', 200)
        self.assertEqual(self.w.balance, 100_000)
        self.assertEqual(self.w.receipts, {})