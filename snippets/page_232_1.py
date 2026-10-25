    def test_old_delivery_does_not_replace_new_generation(self):
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.reissue(1, 'operator')
        self.d.event('late', 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (2, 'pending', 0, 0))

    def test_replayed_delivery_cannot_clear_dispute(self):
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.event('c1', 1, 'dispute', 'customer')
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.event('d2', 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (1, 'delivered', 1, 0))
        with self.assertRaises(ValueError):
            self.d.event('a1', 1, 'activate', 'customer_verified')