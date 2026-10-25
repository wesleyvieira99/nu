    def test_complaint_date_is_before_first_due_date(self):
        plan = self.c.schedule('owner', True)
        self.assertEqual(plan['state'], 'ELIGIBLE')
        self.assertEqual(plan['dues'][0], date(2026, 6, 10))
        with self.assertRaises(ValueError):
            self.c.pay('owner', 0, date(2026, 6, 1))
        self.assertEqual(self.c.paid, {})

    def test_outflow_changes_net_eligibility(self):
        out = Transfer('out', 'owner', date(2026, 5, 29), -1)
        self.c.record(out, 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 0)

    def test_concurrent_payment_is_once_per_installment(self):
        def pay(_):
            return self.c.pay('owner', 0, date(2026, 6, 10))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(pay, range(20)))
        self.assertEqual(set(results), {1800})
        self.assertEqual(sum(self.c.paid.values()), 1800)