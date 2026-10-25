"""Synthetic global credit and per-card budget; not a Nubank risk engine.

Budgets here are lifetime synthetic limits, not a claim about product periods.
SQLite serializes global reservations. Owner is trusted authenticated context.
Production needs fraud controls, issuer/network integration and reserve expiry.
"""
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path


class Credit:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS account(owner TEXT PRIMARY KEY NOT NULL, free INTEGER);
          CREATE TABLE IF NOT EXISTS cards(id TEXT PRIMARY KEY NOT NULL,owner TEXT,
            cap INTEGER,spent INTEGER);
          CREATE TABLE IF NOT EXISTS holds(id TEXT PRIMARY KEY NOT NULL,card TEXT,cents INTEGER);
        ''')

    def seed(self):
        with self.db:
            self.db.execute("INSERT INTO account VALUES('owner',50000)")
            self.db.executemany('INSERT INTO cards VALUES(?,?,?,0)',
                                [('a', 'owner', 80000), ('b', 'owner', 80000)])

    def preview(self, owner, card):
        row = self.db.execute('SELECT a.free,c.cap-c.spent FROM cards c '
            'JOIN account a ON a.owner=c.owner WHERE c.id=? AND c.owner=?',
            (card, owner)).fetchone()
        if not row:
            raise PermissionError('not owned')
        return max(0, min(row))

    # BOOK_CORE_BEGIN
    def reserve(self, owner, ident, card, cents):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty reservation identity required')
        if type(cents) is not int or cents <= 0:
            raise ValueError('integer cents required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            available = self.preview(owner, card)
            old = self.db.execute('SELECT card,cents FROM holds WHERE id=?',
                                  (ident,)).fetchone()
            if old:
                if old != (card, cents):
                    raise ValueError('reservation conflict')
                return ident
            if cents > available:
                raise ValueError('insufficient global credit or card budget')
            self.db.execute('UPDATE account SET free=free-? WHERE owner=?',
                            (cents, owner))
            self.db.execute('UPDATE cards SET spent=spent+? WHERE id=?',
                            (cents, card))
            self.db.execute('INSERT INTO holds VALUES(?,?,?)', (ident, card, cents))
        return ident

    def set_cap(self, owner, card, cap):
        if type(cap) is not int or cap < 0:
            raise ValueError('integer cap required')
        with self.db:
            if self.db.execute('UPDATE cards SET cap=? WHERE id=? AND owner=?',
                               (cap, card, owner)).rowcount != 1:
                raise PermissionError('not owned')
    # BOOK_CORE_END


class CreditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'credit.db'
        self.c = Credit(self.path)
        self.c.seed()

    def tearDown(self):
        self.c.db.close()
        self.tmp.cleanup()

    # BOOK_TEST_BEGIN
    def test_two_cards_cannot_overspend_shared_credit(self):
        barrier = threading.Barrier(2)
        results = []
        def attempt(card):
            client = Credit(self.path)
            barrier.wait()
            try:
                client.reserve('owner', 'hold-' + card, card, 30000)
                results.append('ok')
            except ValueError:
                results.append('declined')
            finally:
                client.db.close()
        threads = [threading.Thread(target=attempt, args=(c,)) for c in ('a', 'b')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ['ok', 'declined'])
        self.assertEqual(self.c.preview('owner', 'a'), 20000)
    # BOOK_TEST_END

    def test_raising_virtual_cap_does_not_create_credit(self):
        self.c.set_cap('owner', 'a', 1000000)
        self.assertEqual(self.c.preview('owner', 'a'), 50000)

    def test_lower_card_cap_restricts_global_credit(self):
        self.c.set_cap('owner', 'a', 10000)
        with self.assertRaises(ValueError):
            self.c.reserve('owner', 'h', 'a', 10001)
        self.assertEqual(self.c.preview('owner', 'b'), 50000)

    def test_retry_does_not_reserve_twice(self):
        self.c.reserve('owner', 'h', 'a', 30000)
        self.c.reserve('owner', 'h', 'a', 30000)
        self.assertEqual(self.c.preview('owner', 'b'), 20000)

    def test_other_owner_denied_before_idempotent_receipt(self):
        self.c.reserve('owner', 'h', 'a', 10000)
        with self.assertRaises(PermissionError):
            self.c.reserve('intruder', 'h', 'a', 10000)

    def test_stale_preview_cannot_authorize(self):
        self.assertEqual(self.c.preview('owner', 'a'), 50000)
        self.c.reserve('owner', 'h1', 'b', 40000)
        with self.assertRaises(ValueError):
            self.c.reserve('owner', 'h2', 'a', 30000)

    def test_conflicting_retry_rejected(self):
        self.c.reserve('owner', 'h', 'a', 10000)
        with self.assertRaises(ValueError):
            self.c.reserve('owner', 'h', 'b', 10000)

    def test_restart_preserves_reservation(self):
        self.c.reserve('owner', 'h', 'a', 10000)
        self.c.db.close()
        self.c = Credit(self.path)
        self.assertEqual(self.c.preview('owner', 'a'), 40000)

    def test_invalid_cents_rejected(self):
        for amount in (0, -1, True, 1.1):
            with self.assertRaises(ValueError):
                self.c.reserve('owner', 'h', 'a', amount)

    def test_invalid_identity_cannot_reserve_credit(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.c.reserve('owner', ident, 'a', 10000)
        self.assertEqual(self.c.preview('owner', 'a'), 50000)
        self.assertEqual(self.c.db.execute(
            'SELECT COUNT(*) FROM holds').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
