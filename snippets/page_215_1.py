    def test_three_refunds_reduce_exactly_once(self):
        for i, cents in enumerate((3333, 3333, 3334)):
            refund = Entry('r' + str(i), 'refund', cents, 'p')
            self.s.append(refund)
            self.s.append(refund)
        result = explain(self.s.snapshot())
        self.assertEqual(result['refunds'], 10000)
        self.assertEqual(result['amount_due'], 0)
        self.assertEqual(result['revision'], 4)

    def test_old_snapshot_does_not_change_after_new_credit(self):
        old = self.s.snapshot()
        self.s.append(Entry('r', 'refund', 5000, 'p'))
        self.assertEqual(explain(old)['amount_due'], 10000)
        self.assertEqual(explain(self.s.snapshot())['amount_due'], 5000)