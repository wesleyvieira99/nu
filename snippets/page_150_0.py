def test_hide_chart_keeps_financial_information(self):
    before = self.screen.view()
    self.screen.show_chart = False
    after = self.screen.view()
    for key in ('period', 'total_cents', 'due_date'):
        self.assertEqual(before[key], after[key])
    self.assertIsNone(after['chart'])

def test_empty_period(self):
    self.screen.select_period(Invoice('2026-11', 1, 0, '2026-12-10', ()))
    self.assertEqual(self.screen.view()['total_cents'], 0)

def test_refund_is_signed(self):
    self.assertEqual(self.screen.view()['total_cents'], 900)

def test_stale_revision_ignored(self):
    self.screen.apply(replace(self.invoice, revision=2))
    self.assertFalse(self.screen.apply(self.invoice))
    self.assertEqual(self.screen.invoice.revision, 2)