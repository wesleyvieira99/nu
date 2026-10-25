"""Synthetic dispute workflow, not Nubank software or a fraud classifier.

SQLite models one durable authority. Roles are injected trusted server context,
not caller-supplied credentials. Production needs identity, scoped access,
evidence retention, legal policy and independently validated review decisions.
Device evidence alone never produces a consent finding in this model.
"""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Dispute:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('''CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY, action_id TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL)''')

    def history(self):
        return [json.loads(row[0]) for row in self.db.execute(
            'SELECT payload FROM events ORDER BY seq')]

    # BOOK_CORE_BEGIN
    def append(self, action_id, expected, actor, role, kind, evidence):
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError('nonempty action identity required')
        event = dict(actor=actor, role=role, kind=kind, evidence=evidence)
        payload = json.dumps(event, sort_keys=True)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload FROM events WHERE action_id=?',
                                  (action_id,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError('idempotency conflict')
                return self.history()
            history = self.history()
            if expected != len(history):
                raise ValueError('stale revision')
            allowed = {'evidence': 'analyst', 'decision': 'reviewer',
                       'appeal': 'customer', 'review': 'reviewer'}
            if kind not in allowed or allowed[kind] != role:
                raise PermissionError('role not authorized')
            if kind == 'decision' and not any(
                    e['kind'] == 'evidence' for e in history):
                raise ValueError('no evidence dossier')
            validate_transition(history, event)
            self.db.execute('INSERT INTO events VALUES(?,?,?)',
                            (expected + 1, action_id, payload))
        return self.history()
    # BOOK_CORE_END

    def close(self):
        self.db.close()


def validate_transition(history, event):
    kind = event['kind']
    prior = [e for e in history if e['kind'] in {'decision', 'review'}]
    if kind == 'evidence':
        if set(event['evidence']) != {'digest', 'category'}:
            raise ValueError('only minimized evidence references')
        if len(event['evidence']['digest']) != 64:
            raise ValueError('invalid evidence digest')
    elif kind == 'decision':
        if prior or not event['evidence'].get('policy'):
            raise ValueError('initial decision requires policy and unique stage')
    elif kind == 'appeal':
        if not prior or any(e['kind'] == 'appeal' for e in history):
            raise ValueError('appeal requires decision; one appeal in this model')
    elif kind == 'review':
        if not history or history[-1]['kind'] != 'appeal':
            raise ValueError('review requires pending appeal')
        if prior[-1]['actor'] == event['actor']:
            raise PermissionError('independent reviewer required')
        if not event['evidence'].get('policy'):
            raise ValueError('policy required')


class DisputeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'dispute.db'
        self.d = Dispute(self.path)
        self.ev = {'digest': hashlib.sha256(b'device evidence').hexdigest(),
                   'category': 'device_access'}

    def tearDown(self):
        self.d.close()
        self.tmp.cleanup()

    def seed(self):
        self.d.append('e', 0, 'a', 'analyst', 'evidence', self.ev)
        self.d.append('d', 1, 'r1', 'reviewer', 'decision', {'policy': 'v1'})

    # BOOK_TEST_BEGIN
    def test_appeal_requires_independent_reviewer(self):
        self.seed()
        self.d.append('a', 2, 'owner', 'customer', 'appeal', {})
        with self.assertRaises(PermissionError):
            self.d.append('r', 3, 'r1', 'reviewer', 'review', {'policy': 'v2'})
        self.assertEqual(len(self.d.history()), 3)
        self.d.append('r', 3, 'r2', 'reviewer', 'review', {'policy': 'v2'})
        self.assertEqual(self.d.history()[1]['evidence']['policy'], 'v1')

    def test_restart_and_retry_preserve_one_evidence(self):
        self.d.append('e', 0, 'a', 'analyst', 'evidence', self.ev)
        self.d.close()
        self.d = Dispute(self.path)
        result = self.d.append('e', 0, 'a', 'analyst', 'evidence', self.ev)
        self.assertEqual(len(result), 1)
        self.assertNotIn('consent', result[0]['evidence'])
    # BOOK_TEST_END

    def test_conflicting_retry_rejected(self):
        self.seed()
        with self.assertRaises(ValueError):
            self.d.append('e', 0, 'other', 'analyst', 'evidence', self.ev)

    def test_stale_revision_rejected(self):
        self.seed()
        with self.assertRaises(ValueError):
            self.d.append('a', 1, 'owner', 'customer', 'appeal', {})

    def test_decision_without_evidence_rejected(self):
        with self.assertRaises(ValueError):
            self.d.append('d', 0, 'r', 'reviewer', 'decision', {'policy': 'v1'})

    def test_wrong_role_rejected(self):
        with self.assertRaises(PermissionError):
            self.d.append('e', 0, 'owner', 'customer', 'evidence', self.ev)
        with self.assertRaises(PermissionError):
            self.d.append('bad', 0, 'owner', None, 'unknown', {})

    def test_sensitive_payload_rejected(self):
        with self.assertRaises(ValueError):
            self.d.append('e', 0, 'a', 'analyst', 'evidence', {'password': '1234'})

    def test_repeated_initial_decision_rejected(self):
        self.seed()
        with self.assertRaises(ValueError):
            self.d.append('d2', 2, 'r2', 'reviewer', 'decision', {'policy': 'v2'})

    def test_invalid_identity_cannot_bypass_deduplication(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.d.append(ident, 0, 'a', 'analyst', 'evidence', self.ev)
        self.assertEqual(self.d.history(), [])
        with self.assertRaises(sqlite3.IntegrityError):
            with self.d.db:
                self.d.db.execute('INSERT INTO events VALUES(1,NULL,?)', ('{}',))


if __name__ == '__main__':
    unittest.main()
