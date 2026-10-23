def test_pending_has_no_paid_claim(self):
    self.assertEqual(self.make()['body']['label'], 'Autorização pendente')

def test_reversed_has_explicit_status(self):
    doc = self.make(status='reversed', revision=2)
    self.assertEqual(doc['body']['label'], 'Compra estornada')
    self.assertEqual(doc['body']['revision'], 2)

def test_owner_not_in_shareable_body(self):
    self.assertNotIn('owner', self.make()['body'])
    self.assertNotIn('alice', canonical(self.make()).decode())

def test_wrong_subject_is_denied(self):
    with self.assertRaises(PermissionError):
        export_record(self.purchase, 'bob', self.secret)

def test_same_snapshot_same_document(self):
    self.assertEqual(self.make(), self.make())