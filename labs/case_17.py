"""One benefit balance, explicit redemption preview. Synthetic executable model.
Points use hundredths of a point; BRL uses cents. Rates are supplied quotations,
never inferred from the individual public complaint. In-memory locking is not
production atomicity. Quote issuance requires an authenticated pricing service.
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
class Quote:
    quote_id: str
    owner: str
    points_minor: int
    cash_cents: int
    balance_version: int
    expires_at: int


class Benefits:
    def __init__(self, owner, points_minor):
        identifier(owner)
        if type(points_minor) is not int or points_minor < 0:
            raise ValueError('invalid points')
        self.owner, self.points = owner, points_minor
        self.version, self.cash = 1, 0
        self.quotes, self.receipts, self.lock = {}, {}, RLock()

    def issue(self, quote, source):
        with self.lock:
            identifier(quote.quote_id)
            identifier(quote.owner)
            if type(quote.balance_version) is not int or quote.balance_version < 1:
                raise ValueError('invalid balance version')
            if source != 'pricing' or quote.owner != self.owner:
                raise PermissionError('quote issuer')
            if any(type(v) is not int or v <= 0 for v in
                   (quote.points_minor, quote.cash_cents, quote.expires_at)):
                raise ValueError('invalid units')
            if quote.quote_id in self.quotes:
                raise ValueError('quote already issued')
            self.quotes[quote.quote_id] = quote

    # BOOK CORE START
    def redeem(self, actor, quote_id, choice, key, now):
        with self.lock:
            for value in (actor, quote_id, key):
                identifier(value)
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if actor != self.owner:
                raise PermissionError('account scope')
            if choice != 'cash' or not key:
                raise ValueError('explicit supported choice required')
            command = (quote_id, choice)
            if key in self.receipts:
                old, receipt = self.receipts[key]
                if old != command:
                    raise ValueError('idempotency conflict')
                return receipt
            quote = self.quotes[quote_id]
            if now >= quote.expires_at:
                raise ValueError('quote expired')
            if quote.balance_version != self.version:
                raise ValueError('balance changed; preview again')
            if quote.points_minor > self.points:
                raise ValueError('insufficient points')
            self.points -= quote.points_minor
            self.cash += quote.cash_cents
            self.version += 1
            receipt = (quote_id, quote.points_minor, quote.cash_cents)
            self.receipts[key] = (command, receipt)
            return receipt
    # BOOK CORE END


class BenefitTests(unittest.TestCase):
    def setUp(self):
        self.b = Benefits('owner', 1_907_136)
        self.q = Quote('q1', 'owner', 1_907_136, 57_791, 1, 200)
        self.b.issue(self.q, 'pricing')

    # BOOK TEST START
    def test_same_balance_cannot_be_spent_twice(self):
        self.b.redeem('owner', 'q1', 'cash', 'a', 100)
        with self.assertRaises(ValueError):
            self.b.redeem('owner', 'q1', 'cash', 'b', 101)
        self.assertEqual(self.b.points, 0)
        self.assertEqual(self.b.cash, 57_791)

    def test_retry_preserves_original_receipt(self):
        first = self.b.redeem('owner', 'q1', 'cash', 'a', 100)
        retry = self.b.redeem('owner', 'q1', 'cash', 'a', 900)
        self.assertEqual(first, retry)
        self.assertEqual(self.b.cash, 57_791)

    def test_expired_preview_has_no_financial_effect(self):
        with self.assertRaises(ValueError):
            self.b.redeem('owner', 'q1', 'cash', 'a', 200)
        self.assertEqual(self.b.points, 1_907_136)
        self.assertEqual(self.b.cash, 0)
        self.assertEqual(self.b.receipts, {})
    # BOOK TEST END

    def test_concurrent_choices_only_one_commit(self):
        def commit(key):
            try:
                return self.b.redeem('owner', 'q1', 'cash', key, 100)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(commit, ['a', 'b']))
        self.assertEqual(sum(x is not None for x in results), 1)

    def test_wrong_owner_cannot_read_receipt(self):
        self.b.redeem('owner', 'q1', 'cash', 'a', 100)
        with self.assertRaises(PermissionError):
            self.b.redeem('other', 'q1', 'cash', 'a', 100)

    def test_unsupported_choice(self):
        with self.assertRaises(ValueError):
            self.b.redeem('owner', 'q1', 'miles', 'a', 100)
        self.assertEqual(self.b.cash, 0)

    def test_unsigned_quote(self):
        with self.assertRaises(PermissionError):
            self.b.issue(Quote('q2', 'owner', 1, 999_999, 1, 200), 'app')

    def test_quote_not_replaced(self):
        with self.assertRaises(ValueError):
            self.b.issue(self.q, 'pricing')

    def test_conflicting_retry(self):
        self.b.redeem('owner', 'q1', 'cash', 'a', 100)
        with self.assertRaises(ValueError):
            self.b.redeem('owner', 'q2', 'cash', 'a', 100)

    def test_amount_type_validation(self):
        for value in (True, 0, -1, 1.1):
            with self.assertRaises(ValueError):
                self.b.issue(Quote('bad', 'owner', value, 1, 1, 200), 'pricing')


    def test_invalid_clock_has_no_effect(self):
        for now in (float('nan'), float('inf'), True, -1):
            with self.assertRaises(ValueError):
                self.b.redeem('owner', 'q1', 'cash', 'a', now)
        self.assertEqual(self.b.cash, 0)

    def test_missing_owner_and_quote_identity_rejected(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                Benefits(value, 100)
            with self.assertRaises(ValueError):
                self.b.issue(Quote(value, 'owner', 1, 1, 1, 200), 'pricing')
        self.assertEqual(set(self.b.quotes), {'q1'})

    def test_invalid_key_cannot_consume_quote(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                self.b.redeem('owner', 'q1', 'cash', value, 100)
        self.assertEqual(self.b.cash, 0)
        self.assertEqual(self.b.points, 1_907_136)

if __name__ == '__main__':
    unittest.main()
