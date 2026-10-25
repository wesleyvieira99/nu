"""Synthetic two-database payment intent and idempotent provider.

Not a NuPay reproduction. Provider idempotency is an explicit assumption,
not a claim of exactly-once networking. No interest, bank calls, credentials
or merchant cancellation is modeled. Each process uses its own connection.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Provider:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS charges('
                        'key TEXT PRIMARY KEY NOT NULL,payload TEXT,receipt TEXT)')

    def charge(self, key, payload):
        if not isinstance(key, str) or not key.strip():
            raise ValueError('nonempty provider identity required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload,receipt FROM charges WHERE key=?',
                                  (key,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError('provider conflict')
                return old[1]
            receipt = 'provider:' + key
            self.db.execute('INSERT INTO charges VALUES(?,?,?)',
                            (key, payload, receipt))
            return receipt


class IntentClient:
    def __init__(self, path, provider):
        self.db = sqlite3.connect(path)
        self.provider = provider
        self.db.execute('CREATE TABLE IF NOT EXISTS intents('
                        'key TEXT PRIMARY KEY NOT NULL,payload TEXT,receipt TEXT)')

    # BOOK_CORE_BEGIN
    def pay(self, key, amount, merchant, timeout_after_provider=False):
        if not isinstance(key, str) or not key.strip():
            raise ValueError('nonempty intent identity required')
        if type(amount) is not int or amount <= 0 or not merchant:
            raise ValueError('invalid intent')
        payload = json.dumps([amount, merchant])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload,receipt FROM intents WHERE key=?',
                                  (key,)).fetchone()
            if old and old[0] != payload:
                raise ValueError('intent conflict')
            if old and old[1]:
                return old[1]
            self.db.execute('INSERT OR IGNORE INTO intents VALUES(?,?,NULL)',
                            (key, payload))
        receipt = self.provider.charge(key, payload)
        if timeout_after_provider:
            raise TimeoutError('provider committed; local outcome unknown')
        with self.db:
            self.db.execute('UPDATE intents SET receipt=? WHERE key=?',
                            (receipt, key))
        return receipt

    def state(self, key):
        row = self.db.execute('SELECT receipt FROM intents WHERE key=?',
                              (key,)).fetchone()
        return 'absent' if row is None else ('confirmed' if row[0] else 'unknown')
    # BOOK_CORE_END


class IntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.p = Provider(self.path / 'provider.db')
        self.c = IntentClient(self.path / 'client.db', self.p)

    def tearDown(self):
        self.c.db.close()
        self.p.db.close()
        self.tmp.cleanup()

    def charges(self):
        return self.p.db.execute('SELECT COUNT(*) FROM charges').fetchone()[0]

    # BOOK_TEST_BEGIN
    def test_timeout_restart_and_retry_produce_one_charge(self):
        with self.assertRaises(TimeoutError):
            self.c.pay('intent1', 90000, 'merchant', True)
        self.assertEqual(self.c.state('intent1'), 'unknown')
        self.assertEqual(self.charges(), 1)
        self.c.db.close()
        self.c = IntentClient(self.path / 'client.db', self.p)
        self.assertEqual(self.c.pay('intent1', 90000, 'merchant'),
                         'provider:intent1')
        self.assertEqual(self.charges(), 1)
        self.assertEqual(self.c.state('intent1'), 'confirmed')

    def test_same_amount_can_be_two_explicit_purchases(self):
        self.c.pay('intent1', 90000, 'merchant')
        self.c.pay('intent2', 90000, 'merchant')
        self.assertEqual(self.charges(), 2)
    # BOOK_TEST_END

    def test_same_key_different_amount_conflicts(self):
        self.c.pay('i', 100, 'm')
        with self.assertRaises(ValueError):
            self.c.pay('i', 101, 'm')
        self.assertEqual(self.charges(), 1)

    def test_same_key_different_merchant_conflicts(self):
        self.c.pay('i', 100, 'm')
        with self.assertRaises(ValueError):
            self.c.pay('i', 100, 'other')

    def test_repeated_timeout_keeps_single_provider_effect(self):
        for _ in range(3):
            with self.assertRaises(TimeoutError):
                self.c.pay('i', 100, 'm', True)
        self.assertEqual(self.charges(), 1)

    def test_invalid_amount_has_no_intent(self):
        for amount in (True, 1.2, 0, -1):
            with self.assertRaises(ValueError):
                self.c.pay('i', amount, 'm')
        self.assertEqual(self.c.state('i'), 'absent')

    def test_provider_enforces_its_own_payload_binding(self):
        self.p.charge('i', '[100,"m"]')
        with self.assertRaises(ValueError):
            self.p.charge('i', '[101,"m"]')

    def test_confirmed_retry_returns_original_receipt(self):
        self.assertEqual(self.c.pay('i', 100, 'm'), self.c.pay('i', 100, 'm'))
        self.assertEqual(self.charges(), 1)

    def test_invalid_identity_does_not_persist_or_charge(self):
        for ident in (None, '', ' ', 1):
            with self.assertRaises(ValueError):
                self.c.pay(ident, 100, 'm')
        self.assertEqual(self.charges(), 0)
        self.assertEqual(self.c.db.execute(
            'SELECT COUNT(*) FROM intents').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
