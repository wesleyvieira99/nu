def test_multidimensional_reservation_is_atomic(self):
    with self.assertRaises(RuntimeError):
        self.capacity.allocate('a', {'cpu': 2, 'ip': 6})
    self.assertEqual(self.capacity.allocations, {})

def test_same_token_not_reserved_twice(self):
    self.assertTrue(self.capacity.allocate('a', {'cpu': 3}))
    self.assertFalse(self.capacity.allocate('a', {'cpu': 3}))
    self.assertEqual(len(self.capacity.allocations), 1)

def test_conflicting_token(self):
    self.capacity.allocate('a', {'cpu': 3})
    with self.assertRaises(ValueError):
        self.capacity.allocate('a', {'cpu': 4})

def test_concurrent_demands_cannot_overbook(self):
    barrier = threading.Barrier(2)
    def attempt(token):
        barrier.wait()
        try:
            self.capacity.allocate(token, {'cpu': 3})
            return 'accepted'
        except RuntimeError:
            return 'rejected'
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, ['a', 'b']))
    self.assertEqual(sorted(results), ['accepted', 'rejected'])
