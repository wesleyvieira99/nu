def test_old_client_gets_fallback(self):
    self.assertEqual(self.publisher.select({'text'}, 1, self.old), self.old)

def test_capable_client_gets_active_revision(self):
    self.assertEqual(self.publisher.select({'text', 'chart'}, 1, self.old),
                     self.new)

def test_revision_cannot_change(self):
    changed = Manifest('r1', 1, ('chart',), 'view-invoice', 'Fatura')
    with self.assertRaises(ValueError):
        self.publisher.publish(changed)

def test_missing_accessibility_rejected(self):
    with self.assertRaises(ValueError):
        validate(Manifest('r3', 1, ('text',), 'view-invoice', ''))

def test_rollback_selects_old_revision(self):
    self.publisher.activate('r1')
    self.assertEqual(self.publisher.select({'text', 'chart'}, 1, self.old),
                     self.old)