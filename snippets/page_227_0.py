    def test_cache_does_not_authorize(self):
        with self.assertRaises(RuntimeError):
            self.w.withdraw(self.s.owner, 'a', 1000, self.s, 101, False)
        self.assertEqual(self.w.balance, 10_000)
        self.assertEqual(self.w.receipts, {})

    def test_retry_after_commit_returns_receipt(self):
        first = self.w.withdraw(self.s.owner, 'a', 1000, self.s, 101)
        retry = self.w.withdraw(self.s.owner, 'a', 1000, self.s, 900, False)
        self.assertEqual(first, retry)
        self.assertEqual(self.w.balance, 9000)

    def test_parallel_commands_cannot_spend_same_version(self):
        def attempt(key):
            try:
                return self.w.withdraw(self.s.owner, key, 7000, self.s, 101)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ['a', 'b']))
        self.assertEqual(sum(x is not None for x in results), 1)
        self.assertEqual(self.w.balance, 3000)