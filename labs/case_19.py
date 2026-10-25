"""Purpose before FX quotation; synthetic external proposal.
No actual FX pricing, taxes, remittance or bank integration. Capability and quote
issuers are trusted adapters in this model; production needs authenticated
contracts, a durable ledger and explicit policy/market-data ownership.
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
class FXQuote:
    quote_id: str
    owner: str
    purpose: str
    currency: str
    country: str
    debit_cents: int
    foreign_minor: int
    capability_version: int
    expires_at: int


class GlobalWallet:
    def __init__(self, owner, balance_cents):
        identifier(owner)
        if type(balance_cents) is not int or balance_cents < 0:
            raise ValueError('invalid initial balance')
        self.owner, self.balance = owner, balance_cents
        self.version, self.allowed = 1, {('card_spend', 'EUR', 'IE')}
        self.quotes, self.receipts, self.foreign = {}, {}, {}
        self.lock = RLock()

    def issue(self, quote, source):
        with self.lock:
            for value in (quote.quote_id, quote.owner, quote.purpose,
                          quote.currency, quote.country):
                identifier(value)
            if type(quote.capability_version) is not int:
                raise ValueError('integer capability version required')
            if source != 'pricing' or quote.owner != self.owner:
                raise PermissionError('quote scope')
            if (quote.purpose, quote.currency, quote.country) not in self.allowed:
                raise ValueError('unsupported purpose before FX')
            if any(type(v) is not int or v <= 0 for v in
                   (quote.debit_cents, quote.foreign_minor, quote.expires_at)):
                raise ValueError('invalid amounts')
            if quote.capability_version != self.version or quote.quote_id in self.quotes:
                raise ValueError('invalid quote identity or version')
            self.quotes[quote.quote_id] = quote

    # BOOK CORE START
    def commit(self, actor, quote_id, key, now):
        with self.lock:
            for value in (actor, quote_id, key):
                identifier(value)
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if actor != self.owner:
                raise PermissionError('account scope')
            if not key:
                raise ValueError('idempotency key required')
            if key in self.receipts:
                if self.receipts[key][0] != quote_id:
                    raise ValueError('idempotency conflict')
                return self.receipts[key]
            quote = self.quotes[quote_id]
            capability = (quote.purpose, quote.currency, quote.country)
            if quote.capability_version != self.version:
                raise ValueError('capability changed; start again')
            if capability not in self.allowed or now >= quote.expires_at:
                raise ValueError('not executable')
            if quote.debit_cents > self.balance:
                raise ValueError('insufficient funds')
            if any(r[0] == quote_id for r in self.receipts.values()):
                raise ValueError('quote already consumed')
            self.balance -= quote.debit_cents
            self.foreign[quote.currency] = self.foreign.get(quote.currency, 0) + \
                quote.foreign_minor
            receipt = (quote_id, quote.debit_cents, quote.foreign_minor)
            self.receipts[key] = receipt
            return receipt
    # BOOK CORE END

    def update_capabilities(self, allowed, source):
        with self.lock:
            if source != 'product-policy':
                raise PermissionError('policy owner')
            self.allowed, self.version = set(allowed), self.version + 1


class GlobalTests(unittest.TestCase):
    def setUp(self):
        self.w = GlobalWallet('owner', 100_000)
        self.q = FXQuote('q', 'owner', 'card_spend', 'EUR', 'IE',
                         10_000, 1500, 1, 200)
        self.w.issue(self.q, 'pricing')

    # BOOK TEST START
    def test_unsupported_transfer_never_debits(self):
        q = FXQuote('no', 'owner', 'external_transfer', 'EUR', 'IE',
                    10_000, 1500, 1, 200)
        with self.assertRaises(ValueError):
            self.w.issue(q, 'pricing')
        self.assertEqual(self.w.balance, 100_000)
        self.assertNotIn('no', self.w.quotes)

    def test_capability_change_invalidates_old_preview(self):
        self.w.update_capabilities(set(), 'product-policy')
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'a', 100)
        self.assertEqual(self.w.foreign, {})

    def test_expiry_does_not_trigger_reverse_conversion(self):
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'a', 200)
        self.assertEqual(self.w.balance, 100_000)
        self.assertEqual(self.w.receipts, {})
    # BOOK TEST END

    def test_receipt_retry_after_policy_change(self):
        first = self.w.commit('owner', 'q', 'a', 100)
        self.w.update_capabilities(set(), 'product-policy')
        self.assertEqual(self.w.commit('owner', 'q', 'a', 300), first)
        self.assertEqual(self.w.balance, 90_000)

    def test_parallel_duplicate(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.w.commit('owner', 'q', 'a', 100),
                                    range(20)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(self.w.foreign['EUR'], 1500)

    def test_second_key_cannot_reuse_quote(self):
        self.w.commit('owner', 'q', 'a', 100)
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'b', 100)

    def test_wrong_owner(self):
        with self.assertRaises(PermissionError):
            self.w.commit('other', 'q', 'a', 100)

    def test_conflicting_retry(self):
        self.w.commit('owner', 'q', 'a', 100)
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'other-quote', 'a', 100)

    def test_untrusted_pricing_or_policy(self):
        with self.assertRaises(PermissionError):
            self.w.issue(self.q, 'app')
        with self.assertRaises(PermissionError):
            self.w.update_capabilities(set(), 'app')

    def test_insufficient_balance(self):
        self.w.balance = 9999
        with self.assertRaises(ValueError):
            self.w.commit('owner', 'q', 'a', 100)
        self.assertEqual(self.w.foreign, {})


    def test_invalid_clock_has_no_effect(self):
        for now in (float('nan'), float('inf'), True, -1):
            with self.assertRaises(ValueError):
                self.w.commit('owner', 'q', 'a', now)
        self.assertEqual(self.w.balance, 100_000)

    def test_invalid_initial_balance(self):
        for balance in (float('nan'), 1.1, True, -1):
            with self.assertRaises(ValueError):
                GlobalWallet('owner', balance)


    def test_missing_owner_or_quote_id_rejected(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                GlobalWallet(value, 100)
            quote = FXQuote(value, 'owner', 'card_spend', 'EUR', 'IE',
                            100, 1, 1, 200)
            with self.assertRaises(ValueError):
                self.w.issue(quote, 'pricing')
        self.assertEqual(set(self.w.quotes), {'q'})

    def test_invalid_key_cannot_convert(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                self.w.commit('owner', 'q', value, 100)
        self.assertEqual(self.w.balance, 100_000)
        self.assertEqual(self.w.foreign, {})

if __name__ == '__main__':
    unittest.main()
