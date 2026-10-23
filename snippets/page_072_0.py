def test_privacy_changed_while_queued_is_respected(self):
    self.n.configure("u", show_values=True)
    self.n.enqueue(self.event)
    self.n.configure("u", show_values=False)
    self.assertNotIn("123", str(self.n.deliver("e1")))

def test_opt_out_suppresses_delivery(self):
    self.n.enqueue(self.event)
    self.n.configure("u", enabled=False)
    self.assertEqual(self.n.deliver("e1"), {"status": "suppressed"})
    self.assertEqual(len(self.n.sent), 0)

def test_replay_is_identical(self):
    self.n.enqueue(self.event)
    first = self.n.deliver("e1")
    self.n.enqueue(self.event)
    self.assertEqual(self.n.deliver("e1"), first)
    self.assertEqual(len(self.n.sent), 1)

def test_payload_conflict_is_rejected(self):
    self.n.enqueue(self.event)
    with self.assertRaises(ValueError):
        self.n.enqueue(dict(self.event, amount_cents=999))