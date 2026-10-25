    def test_user_sms_claim_cannot_authorize_donor(self):
        event = Event('d', 'request-a', 'donor_authorized', 'owner', 1)
        with self.assertRaises(PermissionError):
            self.p.apply(event, 'owner')
        self.assertEqual(self.p.state, 'WAIT_DONOR')

    def test_late_activation_cannot_revive_cancelled_request(self):
        cancel = Event('c', 'request-a', 'cancelled', 'owner', 1)
        self.p.apply(cancel, 'owner')
        late = Event('a', 'request-a', 'activated', 'recipient', 2)
        with self.assertRaises(ValueError):
            self.p.apply(late, 'recipient')
        self.assertEqual(self.p.state, 'CANCELLED')

    def test_early_activation_requires_reconciliation(self):
        event = Event('a', 'request-a', 'activated', 'recipient', 2)
        with self.assertRaises(ValueError):
            self.p.apply(event, 'recipient')
        self.assertNotIn('a', self.p.seen)
        self.assertEqual(self.p.state, 'WAIT_DONOR')