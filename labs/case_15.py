"""Caixinha withdrawal model, external proposal; synthetic data only.
No bank integration. RLock protects one process, not distributed writers.
Production needs an authorized ledger transaction, durable idempotency,
account-level access control, reconciliation and bounded snapshot retention.
"""
from dataclasses import dataclass
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
import unittest

def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError('nonblank string identity required')
    return value



@dataclass(frozen=True)
class Snapshot:
    owner: str
    balance_cents: int
    version: int
    observed_at: int


class Withdrawals:
    def __init__(self, owner, balance_cents):
        identifier(owner)
        if type(balance_cents) is not int or balance_cents < 0:
            raise ValueError('invalid balance')
        self.owner, self.balance = owner, balance_cents
        self.version, self.receipts, self.lock = 1, {}, RLock()

    def snapshot(self, now):
        with self.lock:
            return Snapshot(self.owner, self.balance, self.version, now)

    # BOOK CORE START
    def withdraw(self, actor, key, cents, snapshot, now, ledger_online=True):
        with self.lock:
            for value in (actor, key, snapshot.owner):
                identifier(value)
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if actor != self.owner or snapshot.owner != actor:
                raise PermissionError('account scope')
            if not key or type(cents) is not int or cents <= 0:
                raise ValueError('invalid command')
            command = (actor, cents)
            if key in self.receipts:
                prior_command, receipt = self.receipts[key]
                if prior_command != command:
                    raise ValueError('idempotency conflict')
                return receipt
            if not ledger_online:
                raise RuntimeError('authority unavailable')
            if not 0 <= now - snapshot.observed_at <= 30:
                raise ValueError('snapshot expired')
            if snapshot.version != self.version:
                raise ValueError('refresh required')
            if cents > self.balance:
                raise ValueError('insufficient funds')
            self.balance -= cents
            self.version += 1
            receipt = (key, cents, self.version)
            self.receipts[key] = (command, receipt)
            return receipt
    # BOOK CORE END


class WithdrawalTests(unittest.TestCase):
    def setUp(self):
        self.w = Withdrawals('synthetic-owner', 10_000)
        self.s = self.w.snapshot(100)

    # BOOK TEST START
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
    # BOOK TEST END

    def test_scope_checked_before_receipt(self):
        self.w.withdraw(self.s.owner, 'a', 1000, self.s, 101)
        with self.assertRaises(PermissionError):
            self.w.withdraw('other', 'a', 1000, self.s, 102)

    def test_conflicting_retry(self):
        self.w.withdraw(self.s.owner, 'a', 1000, self.s, 101)
        with self.assertRaises(ValueError):
            self.w.withdraw(self.s.owner, 'a', 2000, self.s, 101)

    def test_expired_and_future_snapshot(self):
        for now in (99, 131):
            with self.assertRaises(ValueError):
                self.w.withdraw(self.s.owner, str(now), 1000, self.s, now)
        self.assertEqual(self.w.balance, 10_000)

    def test_exact_boundary(self):
        self.w.withdraw(self.s.owner, 'a', 10_000, self.s, 130)
        self.assertEqual(self.w.balance, 0)

    def test_invalid_amounts_never_mutate(self):
        for cents in (True, 1.1, 0, -1, 10_001):
            with self.assertRaises(ValueError):
                self.w.withdraw(self.s.owner, 'a', cents, self.s, 101)
        self.assertEqual(self.w.balance, 10_000)

    def test_unavailable_retry_can_later_succeed(self):
        with self.assertRaises(RuntimeError):
            self.w.withdraw(self.s.owner, 'a', 1000, self.s, 101, False)
        self.w.withdraw(self.s.owner, 'a', 1000, self.s, 102)
        self.assertEqual(len(self.w.receipts), 1)

    def test_other_snapshot_owner(self):
        wrong = Snapshot('other', 10_000, 1, 100)
        with self.assertRaises(PermissionError):
            self.w.withdraw(self.s.owner, 'a', 1000, wrong, 101)


    def test_invalid_clock_has_no_effect(self):
        for now in (float('nan'), float('inf'), True, -1):
            with self.assertRaises(ValueError):
                self.w.withdraw(self.s.owner, 'a', 1000, self.s, now)
        self.assertEqual(self.w.balance, 10_000)

    def test_missing_owner_rejected_before_state(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                Withdrawals(value, 100)

    def test_invalid_command_key_has_no_effect(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                self.w.withdraw(self.s.owner, value, 100, self.s, 101)
        self.assertEqual(self.w.balance, 10_000)
        self.assertEqual(self.w.receipts, {})

if __name__ == '__main__':
    unittest.main()
