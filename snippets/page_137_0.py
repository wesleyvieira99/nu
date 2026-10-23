def test_duplicate(self):
    self.model.ingest(self.event())
    self.assertEqual(self.model.ingest(self.event()), 'duplicate')
    self.assertEqual(len(self.model.state()), 1)

def test_conflicting_identity(self):
    self.model.ingest(self.event())
    with self.assertRaises(ValueError):
        self.model.ingest(self.event(status='delivered'))
    self.assertEqual(self.model.state()[0][2], 'transit')

def test_out_of_order(self):
    self.model.ingest(self.event(seq=5, status='delivered'))
    result = self.model.ingest(self.event(event_id='e2', seq=2))
    self.assertEqual(result, 'stale')
    self.assertEqual(self.model.state()[0][2], 'delivered')

def test_terminal_guard(self):
    self.model.ingest(self.event(status='delivered'))
    with self.assertRaises(ValueError):
        self.model.ingest(self.event(event_id='e2', seq=2))