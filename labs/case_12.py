"""Synthetic card generation and delivery workflow, not Nubank logistics.

One account and one SQLite authority. 'scope' is injected authenticated server
context; production must verify carrier signatures, customer identity, evidence
access and activation factors. Delivery never automatically activates a card.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Delivery:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS card(id INTEGER PRIMARY KEY CHECK(id=1),
            generation INTEGER, carrier TEXT, disputed INTEGER, active INTEGER);
          INSERT OR IGNORE INTO card VALUES(1,1,'pending',0,0);
          CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY NOT NULL,payload TEXT);
        ''')

    def state(self):
        return self.db.execute('SELECT generation,carrier,disputed,active '
                               'FROM card WHERE id=1').fetchone()

    # BOOK_CORE_BEGIN
    def event(self, ident, generation, kind, scope):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty event identity required')
        if type(generation) is not int or generation < 1:
            raise ValueError('positive integer generation required')
        required = {'delivered': 'carrier', 'dispute': 'customer',
                    'activate': 'customer_verified'}
        if kind not in required or required[kind] != scope:
            raise PermissionError('scope mismatch')
        payload = json.dumps([generation, kind, scope])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload FROM events WHERE id=?',
                                  (ident,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError('event conflict')
                return self.state()
            current, carrier, disputed, active = self.state()
            if generation > current:
                raise ValueError('future generation; event not consumed')
            if generation == current:
                if kind == 'delivered':
                    carrier = 'delivered'
                elif kind == 'dispute':
                    disputed, active = 1, 0
                elif kind == 'activate':
                    if disputed:
                        raise ValueError('dispute requires separate resolution')
                    active = 1
                self.db.execute('UPDATE card SET carrier=?,disputed=?,active=? '
                                'WHERE id=1', (carrier, disputed, active))
            self.db.execute('INSERT INTO events VALUES(?,?)', (ident, payload))
        return self.state()
    # BOOK_CORE_END

    def reissue(self, expected_generation, scope):
        if scope != 'operator':
            raise PermissionError('operator required')
        with self.db:
            changed = self.db.execute('UPDATE card SET generation=generation+1, '
                "carrier='pending',disputed=0,active=0 WHERE id=1 AND generation=?",
                (expected_generation,)).rowcount
            if changed != 1:
                raise ValueError('stale generation')


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'delivery.db'
        self.d = Delivery(self.path)

    def tearDown(self):
        self.d.db.close()
        self.tmp.cleanup()

    # BOOK_TEST_BEGIN
    def test_old_delivery_does_not_replace_new_generation(self):
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.reissue(1, 'operator')
        self.d.event('late', 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (2, 'pending', 0, 0))

    def test_replayed_delivery_cannot_clear_dispute(self):
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.event('c1', 1, 'dispute', 'customer')
        self.d.event('d1', 1, 'delivered', 'carrier')
        self.d.event('d2', 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (1, 'delivered', 1, 0))
        with self.assertRaises(ValueError):
            self.d.event('a1', 1, 'activate', 'customer_verified')
    # BOOK_TEST_END

    def test_delivery_is_not_activation(self):
        self.d.event('d', 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state()[-1], 0)

    def test_carrier_cannot_activate(self):
        with self.assertRaises(PermissionError):
            self.d.event('a', 1, 'activate', 'carrier')
        with self.assertRaises(PermissionError):
            self.d.event('bad', 1, 'unknown', None)

    def test_new_generation_cancels_old_activation(self):
        self.d.event('a', 1, 'activate', 'customer_verified')
        self.d.reissue(1, 'operator')
        self.d.event('old-a', 1, 'activate', 'customer_verified')
        self.assertEqual(self.d.state()[-1], 0)

    def test_conflicting_event_id_rejected(self):
        self.d.event('d', 1, 'delivered', 'carrier')
        with self.assertRaises(ValueError):
            self.d.event('d', 2, 'delivered', 'carrier')

    def test_restart_keeps_dispute(self):
        self.d.event('c', 1, 'dispute', 'customer')
        self.d.db.close()
        self.d = Delivery(self.path)
        self.assertEqual(self.d.state()[2], 1)

    def test_stale_reissue_does_not_create_extra_generation(self):
        self.d.reissue(1, 'operator')
        with self.assertRaises(ValueError):
            self.d.reissue(1, 'operator')
        self.assertEqual(self.d.state()[0], 2)

    def test_future_event_can_be_retried_after_generation_exists(self):
        with self.assertRaises(ValueError):
            self.d.event('future', 2, 'delivered', 'carrier')
        self.assertEqual(self.d.db.execute(
            'SELECT COUNT(*) FROM events').fetchone()[0], 0)
        self.d.reissue(1, 'operator')
        self.d.event('future', 2, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (2, 'delivered', 0, 0))

    def test_invalid_event_identity_cannot_be_consumed(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.d.event(ident, 1, 'delivered', 'carrier')
        self.assertEqual(self.d.state(), (1, 'pending', 0, 0))


if __name__ == '__main__':
    unittest.main()
