def test_concurrent_distinct_payments_cannot_overdraw(self):
    barrier = threading.Barrier(2)
    def attempt(operation_id):
        barrier.wait(timeout=10)
        try:
            return self.bank.pay(**self.command(operation_id=operation_id))
        except InsufficientFunds:
            return "insufficient"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ("parallel-a", "parallel-b")))
    self.assertEqual(sum(isinstance(value, dict) for value in results), 1)
    self.assertEqual(results.count("insufficient"), 1)
    self.assert_invariants(balance=300, payments=1)

def test_concurrent_same_operation_has_one_receipt_and_one_debit(self):
    barrier = threading.Barrier(8)
    def retry(_):
        barrier.wait(timeout=10)
        return self.bank.pay(**self.command())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(retry, range(8)))
    self.assertTrue(all(receipt == results[0] for receipt in results))
    self.assert_invariants(balance=300, payments=1)