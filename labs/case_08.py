"""Caso 08: ingestão logística sintética; Python stdlib, sem parceiros reais."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path


class Timeline:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS events (
          event_id TEXT PRIMARY KEY, digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS shipments (
          shipment_id TEXT PRIMARY KEY, seq INTEGER NOT NULL,
          status TEXT NOT NULL, next_step TEXT NOT NULL);
        ''')

    def ingest(self, event, crash=False):
        payload = json.dumps(event, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if event['status'] not in {'transit', 'exception', 'delivered'}:
            raise ValueError('status desconhecido')
        if type(event['seq']) is not int or event['seq'] < 1:
            raise ValueError('sequência inválida')
        with self.db:
            # A decisão de versão deve usar a mesma transação da gravação.
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT digest FROM events WHERE event_id=?',
                                  (event['event_id'],)).fetchone()
            if old:
                if old[0] != digest:
                    raise ValueError('evento conflitante')
                return 'duplicate'
            row = self.db.execute('SELECT seq,status FROM shipments '
                'WHERE shipment_id=?', (event['shipment_id'],)).fetchone()
            self.db.execute('INSERT INTO events VALUES (?,?)',
                            (event['event_id'], digest))
            if row and event['seq'] <= row[0]:
                return 'stale'
            if row and row[1] == 'delivered' and event['status'] != 'delivered':
                raise ValueError('regressão terminal')
            self.db.execute('INSERT OR REPLACE INTO shipments VALUES (?,?,?,?)',
                (event['shipment_id'], event['seq'], event['status'],
                 event['next_step']))
            if crash:
                raise RuntimeError('falha antes do commit')
        return 'applied'

    def state(self):
        return self.db.execute('SELECT * FROM shipments').fetchall()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'events.sqlite'
        self.model = Timeline(self.path)
        self.addCleanup(self.model.db.close)

    def event(self, **changes):
        value = dict(event_id='e1', shipment_id='s1', seq=1,
                     status='transit', next_step='aguardar atualização')
        return dict(value, **changes)

    def test_duplicate(self):
        self.model.ingest(self.event())
        self.assertEqual(self.model.ingest(self.event()), 'duplicate')
        self.assertEqual(len(self.model.state()), 1)

    def test_conflicting_identity(self):
        self.model.ingest(self.event())
        with self.assertRaises(ValueError):
            self.model.ingest(self.event(status='delivered'))
        self.assertEqual(self.model.state()[0][2], 'transit')

    def test_out_of_order(self):
        self.model.ingest(self.event(seq=5, status='delivered'))
        result = self.model.ingest(self.event(event_id='e2', seq=2))
        self.assertEqual(result, 'stale')
        self.assertEqual(self.model.state()[0][2], 'delivered')

    def test_terminal_guard(self):
        self.model.ingest(self.event(status='delivered'))
        with self.assertRaises(ValueError):
            self.model.ingest(self.event(event_id='e2', seq=2))

    def test_atomic_failure_and_retry(self):
        with self.assertRaises(RuntimeError):
            self.model.ingest(self.event(), crash=True)
        self.assertEqual(self.model.state(), [])
        self.assertEqual(self.model.ingest(self.event()), 'applied')

    def test_reopen(self):
        self.model.ingest(self.event())
        other = Timeline(self.path)
        self.addCleanup(other.db.close)
        self.assertEqual(other.ingest(self.event()), 'duplicate')

    def test_write_transaction_precedes_reads(self):
        statements = []
        self.model.db.set_trace_callback(statements.append)
        self.model.ingest(self.event())
        first_select = next(i for i, sql in enumerate(statements)
                            if sql.startswith('SELECT'))
        self.assertLess(statements.index('BEGIN IMMEDIATE'), first_select)

    def test_independent_connections_preserve_highest_sequence(self):
        self.model.ingest(self.event())
        barrier = threading.Barrier(8)
        def attempt(sequence):
            model = Timeline(self.path)
            try:
                barrier.wait(timeout=5)
                return model.ingest(self.event(event_id=f'e{sequence}',
                                               seq=sequence))
            finally:
                model.db.close()
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(attempt, range(2, 10)))
        self.assertTrue(set(results) <= {'applied', 'stale'})
        self.assertEqual(self.model.state()[0][1], 9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
