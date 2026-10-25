"""Synthetic allocation ledger; not Nubank's financial rules.

One SQLite database models received payments and obligations in BRL cents.
Production requires authorized account scope, true settlement evidence,
contractual allocation order, outbox delivery and independent reconciliation.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS obligations(id TEXT PRIMARY KEY NOT NULL, due INTEGER);
          CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY NOT NULL, amount INTEGER,
            plan TEXT, remainder INTEGER);
          CREATE TABLE IF NOT EXISTS allocations(payment TEXT, obligation TEXT,
            amount INTEGER, PRIMARY KEY(payment, obligation));
        ''')

    def add(self, ident, due):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty obligation identity required')
        if type(due) is not int or due < 0:
            raise ValueError('integer cents required')
        with self.db:
            self.db.execute('INSERT INTO obligations VALUES(?,?)', (ident, due))

    # BOOK_CORE_BEGIN
    def apply(self, ident, amount, plan, crash=False):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty payment identity required')
        if type(amount) is not int or amount <= 0:
            raise ValueError('positive integer cents required')
        if any(type(v) is not int or v <= 0 for v in plan.values()):
            raise ValueError('invalid allocation')
        encoded = json.dumps(plan, sort_keys=True)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT amount,plan FROM payments WHERE id=?',
                                  (ident,)).fetchone()
            if old:
                if old != (amount, encoded):
                    raise ValueError('payment conflict')
                return self.receipt(ident)
            if sum(plan.values()) > amount:
                raise ValueError('allocation exceeds received amount')
            for target, value in plan.items():
                changed = self.db.execute('UPDATE obligations SET due=due-? '
                    'WHERE id=? AND due>=?', (value, target, value)).rowcount
                if changed != 1:
                    raise ValueError('unknown or overpaid obligation')
                self.db.execute('INSERT INTO allocations VALUES(?,?,?)',
                                (ident, target, value))
            if crash:
                raise RuntimeError('crash before commit')
            self.db.execute('INSERT INTO payments VALUES(?,?,?,?)',
                            (ident, amount, encoded, amount - sum(plan.values())))
        return self.receipt(ident)
    # BOOK_CORE_END

    def receipt(self, ident):
        row = self.db.execute('SELECT amount,remainder FROM payments WHERE id=?',
                              (ident,)).fetchone()
        applied = self.db.execute('SELECT COALESCE(SUM(amount),0) FROM allocations '
                                 'WHERE payment=?', (ident,)).fetchone()[0]
        assert row[0] == applied + row[1]
        return dict(received=row[0], applied=applied, unapplied=row[1])

    def due(self, ident):
        return self.db.execute('SELECT due FROM obligations WHERE id=?',
                               (ident,)).fetchone()[0]

    def close(self):
        self.db.close()


class AllocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'ledger.db'
        self.l = Ledger(self.path)
        self.l.add('bill', 10000)
        self.l.add('installment', 5000)

    def tearDown(self):
        self.l.close()
        self.tmp.cleanup()

    # BOOK_TEST_BEGIN
    def test_failure_after_first_write_rolls_everything_back(self):
        with self.assertRaises(ValueError):
            self.l.apply('p', 20000, {'bill': 10000, 'installment': 6000})
        self.assertEqual(self.l.due('bill'), 10000)
        self.assertEqual(self.l.due('installment'), 5000)
        self.assertEqual(self.l.db.execute(
            'SELECT COUNT(*) FROM allocations').fetchone()[0], 0)

    def test_restart_retry_does_not_apply_twice(self):
        first = self.l.apply('p', 12000, {'bill': 10000})
        self.l.close()
        self.l = Ledger(self.path)
        self.assertEqual(self.l.apply('p', 12000, {'bill': 10000}), first)
        self.assertEqual(first['unapplied'], 2000)
        self.assertEqual(self.l.due('bill'), 0)
    # BOOK_TEST_END

    def test_crash_before_commit_has_no_effect(self):
        with self.assertRaises(RuntimeError):
            self.l.apply('p', 10000, {'bill': 10000}, crash=True)
        self.assertEqual(self.l.due('bill'), 10000)

    def test_changed_plan_conflicts(self):
        self.l.apply('p', 1000, {'bill': 1000})
        with self.assertRaises(ValueError):
            self.l.apply('p', 1000, {'installment': 1000})

    def test_over_allocation_rejected(self):
        with self.assertRaises(ValueError):
            self.l.apply('p', 100, {'bill': 101})

    def test_fractional_cents_rejected(self):
        with self.assertRaises(ValueError):
            self.l.apply('p', 100.0, {'bill': 100})

    def test_exact_conservation_across_two_targets(self):
        r = self.l.apply('p', 15001, {'bill': 10000, 'installment': 5000})
        self.assertEqual(r, {'received': 15001, 'applied': 15000, 'unapplied': 1})

    def test_second_payment_cannot_overpay_settled_target(self):
        self.l.apply('p1', 10000, {'bill': 10000})
        with self.assertRaises(ValueError):
            self.l.apply('p2', 10000, {'bill': 10000})

    def test_invalid_identity_never_commits_an_allocation(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.l.apply(ident, 100, {'bill': 100})
        self.assertEqual(self.l.due('bill'), 10000)
        self.assertEqual(self.l.db.execute(
            'SELECT COUNT(*) FROM payments').fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.l.db:
                self.l.db.execute('INSERT INTO payments VALUES(NULL,100,?,0)',
                                  ('{}',))


if __name__ == '__main__':
    unittest.main()
