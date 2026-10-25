    def test_failure_after_first_write_rolls_everything_back(self):
        with self.assertRaises(ValueError):
            self.l.apply('p', 20000, {'bill': 10000, 'installment': 6000})
        self.assertEqual(self.l.due('bill'), 10000)
        self.assertEqual(self.l.due('installment'), 5000)
        self.assertEqual(self.l.db.execute(
            'SELECT COUNT(*) FROM allocations').fetchone()[0], 0)

    def test_restart_retry_does_not_apply_twice(self):
        first = self.l.apply('p', 12000, {'bill': 10000})
        self.l.close()
        self.l = Ledger(self.path)
        self.assertEqual(self.l.apply('p', 12000, {'bill': 10000}), first)
        self.assertEqual(first['unapplied'], 2000)
        self.assertEqual(self.l.due('bill'), 0)