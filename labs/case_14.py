"""Synthetic early-repayment quote, funding and execution.

Amounts are integer cents; discount is an externally approved input, not a
calculation of Nubank interest. One account/contract is modeled. Production
needs authorized scope, real contract pricing, settlement, expiry policy,
double-entry accounting and a separately authorized refund path.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Repayment:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS contract(id INTEGER PRIMARY KEY,
            revision INTEGER,settled INTEGER);
          INSERT OR IGNORE INTO contract VALUES(1,1,0);
          CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY NOT NULL,revision INTEGER,
            bill INTEGER,principal INTEGER,discount INTEGER,expires INTEGER,
            received INTEGER DEFAULT 0,executed INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS funding(id TEXT PRIMARY KEY NOT NULL,quote TEXT,cents INTEGER);
        ''')

    def quote(self, ident, bill, principal, discount, expires):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty quote identity required')
        if any(type(x) is not int or x < 0 for x in (bill, principal, discount)):
            raise ValueError('nonnegative integer cents required')
        if principal == 0 or discount > principal:
            raise ValueError('invalid discount')
        revision = self.db.execute('SELECT revision FROM contract').fetchone()[0]
        with self.db:
            self.db.execute('INSERT INTO quotes(id,revision,bill,principal,'
                'discount,expires) VALUES(?,?,?,?,?,?)',
                (ident, revision, bill, principal, discount, expires))

    def receive(self, payment, quote, cents):
        if not isinstance(payment, str) or not payment.strip():
            raise ValueError('nonempty payment identity required')
        if type(cents) is not int or cents <= 0:
            raise ValueError('positive integer cents required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT quote,cents FROM funding WHERE id=?',
                                  (payment,)).fetchone()
            if old:
                if old != (quote, cents):
                    raise ValueError('payment conflict')
                return
            updated = self.db.execute('UPDATE quotes SET received=received+? '
                'WHERE id=? AND executed=0', (cents, quote)).rowcount
            if updated != 1:
                raise ValueError('unknown or executed quote')
            self.db.execute('INSERT INTO funding VALUES(?,?,?)',
                            (payment, quote, cents))

    # BOOK_CORE_BEGIN
    def execute(self, ident, now, crash=False):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT revision,bill,principal,discount,'
                'expires,received,executed FROM quotes WHERE id=?',
                (ident,)).fetchone()
            if not row:
                raise ValueError('unknown quote')
            revision, bill, principal, discount, expires, received, done = row
            needed = bill + principal - discount
            if done:
                return dict(applied=needed, unapplied=received - needed)
            current = self.db.execute('SELECT revision FROM contract').fetchone()[0]
            if now >= expires or revision != current:
                raise ValueError('expired or stale quote; funds remain unapplied')
            if received < needed:
                raise ValueError('full quoted amount not received')
            self.db.execute('UPDATE contract SET revision=revision+1,'
                            'settled=settled+?', (principal,))
            self.db.execute('UPDATE quotes SET executed=1 WHERE id=?', (ident,))
            if crash:
                raise RuntimeError('crash before commit')
        return dict(applied=needed, unapplied=received - needed)
    # BOOK_CORE_END


class RepaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'repayment.db'
        self.r = Repayment(self.path)
        self.r.quote('q', bill=5000, principal=10000, discount=1000, expires=100)

    def tearDown(self):
        self.r.db.close()
        self.tmp.cleanup()

    # BOOK_TEST_BEGIN
    def test_received_is_not_executed_and_crash_rolls_back(self):
        self.r.receive('p', 'q', 14000)
        with self.assertRaises(RuntimeError):
            self.r.execute('q', 90, crash=True)
        self.assertEqual(self.r.db.execute('SELECT settled FROM contract')
                         .fetchone()[0], 0)
        self.r.db.close()
        self.r = Repayment(self.path)
        self.assertEqual(self.r.execute('q', 90)['applied'], 14000)
        self.assertEqual(self.r.execute('q', 200)['applied'], 14000)
        self.assertEqual(self.r.db.execute('SELECT settled FROM contract')
                         .fetchone()[0], 10000)
    # BOOK_TEST_END

    def test_partial_funding_is_not_silently_applied(self):
        self.r.receive('p', 'q', 9000)
        with self.assertRaises(ValueError):
            self.r.execute('q', 90)
        self.assertEqual(self.r.db.execute('SELECT received,executed FROM quotes')
                         .fetchone(), (9000, 0))

    def test_expiry_preserves_received_money_for_resolution(self):
        self.r.receive('p', 'q', 14000)
        with self.assertRaises(ValueError):
            self.r.execute('q', 100)
        self.assertEqual(self.r.db.execute('SELECT received FROM quotes')
                         .fetchone()[0], 14000)

    def test_payment_retry_is_idempotent(self):
        self.r.receive('p', 'q', 14000)
        self.r.receive('p', 'q', 14000)
        self.assertEqual(self.r.execute('q', 90)['unapplied'], 0)

    def test_conflicting_payment_rejected(self):
        self.r.receive('p', 'q', 100)
        with self.assertRaises(ValueError):
            self.r.receive('p', 'q', 101)

    def test_second_quote_becomes_stale_after_execution(self):
        self.r.quote('q2', 0, 5000, 100, 100)
        self.r.receive('p', 'q', 14000)
        self.r.execute('q', 90)
        self.r.receive('p2', 'q2', 4900)
        with self.assertRaises(ValueError):
            self.r.execute('q2', 91)

    def test_overpayment_is_explicit_remainder(self):
        self.r.receive('p', 'q', 14001)
        self.assertEqual(self.r.execute('q', 90), {'applied': 14000, 'unapplied': 1})

    def test_invalid_discount_rejected(self):
        with self.assertRaises(ValueError):
            self.r.quote('bad', 0, 100, 101, 100)

    def test_invalid_identity_cannot_duplicate_funding(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.r.receive(ident, 'q', 100)
            with self.assertRaises(ValueError):
                self.r.quote(ident, 0, 100, 0, 100)
        self.assertEqual(self.r.db.execute('SELECT received FROM quotes')
                         .fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
