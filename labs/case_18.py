"""Portability evidence journal, not a telecom implementation.
Synthetic actors stand for already authenticated integrations. Production
requires signed callbacks, partner agreements, durable compare-and-swap,
number-holder verification and a separate billing-adjustment authority.
"""
from dataclasses import dataclass
from threading import RLock
import unittest

def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError('nonblank string identity required')
    return value



@dataclass(frozen=True)
class Event:
    event_id: str
    request_id: str
    kind: str
    source: str
    sequence: int


class Portability:
    SOURCES = {'sms_sent': 'recipient', 'donor_authorized': 'donor',
               'activated': 'recipient', 'cancelled': 'owner'}

    def __init__(self, request_id):
        identifier(request_id)
        self.request_id, self.state = request_id, 'REQUESTED'
        self.seen, self.journal, self.sequences = {}, [], {}
        self.lock = RLock()

    # BOOK CORE START
    def apply(self, event, authenticated_source):
        with self.lock:
            for value in (event.event_id, event.request_id, event.kind, event.source):
                identifier(value)
            if event.request_id != self.request_id:
                raise ValueError('request scope')
            if event.source != authenticated_source:
                raise PermissionError('untrusted source')
            if self.SOURCES.get(event.kind) != event.source:
                raise PermissionError('event authority')
            if type(event.sequence) is not int or event.sequence < 1:
                raise ValueError('invalid sequence')
            if event.event_id in self.seen:
                if self.seen[event.event_id] != event:
                    raise ValueError('event identity conflict')
                return self.state
            if event.sequence <= self.sequences.get(event.source, 0):
                raise ValueError('out-of-order; reconcile')
            allowed = {'sms_sent': ('REQUESTED',),
                       'donor_authorized': ('WAIT_DONOR',),
                       'activated': ('AUTHORIZED',),
                       'cancelled': ('REQUESTED', 'WAIT_DONOR', 'AUTHORIZED')}
            if self.state not in allowed[event.kind]:
                raise ValueError('invalid transition; reconcile')
            self.state = {'sms_sent': 'WAIT_DONOR', 'donor_authorized':
                          'AUTHORIZED', 'activated': 'ACTIVE',
                          'cancelled': 'CANCELLED'}[event.kind]
            self.seen[event.event_id] = event
            self.sequences[event.source] = event.sequence
            self.journal.append(event)
            return self.state
    # BOOK CORE END


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.p = Portability('request-a')
        self.sms = Event('s', 'request-a', 'sms_sent', 'recipient', 1)
        self.p.apply(self.sms, 'recipient')

    # BOOK TEST START
    def test_user_sms_claim_cannot_authorize_donor(self):
        event = Event('d', 'request-a', 'donor_authorized', 'owner', 1)
        with self.assertRaises(PermissionError):
            self.p.apply(event, 'owner')
        self.assertEqual(self.p.state, 'WAIT_DONOR')

    def test_late_activation_cannot_revive_cancelled_request(self):
        cancel = Event('c', 'request-a', 'cancelled', 'owner', 1)
        self.p.apply(cancel, 'owner')
        late = Event('a', 'request-a', 'activated', 'recipient', 2)
        with self.assertRaises(ValueError):
            self.p.apply(late, 'recipient')
        self.assertEqual(self.p.state, 'CANCELLED')

    def test_early_activation_requires_reconciliation(self):
        event = Event('a', 'request-a', 'activated', 'recipient', 2)
        with self.assertRaises(ValueError):
            self.p.apply(event, 'recipient')
        self.assertNotIn('a', self.p.seen)
        self.assertEqual(self.p.state, 'WAIT_DONOR')
    # BOOK TEST END

    def test_happy_path(self):
        self.p.apply(Event('d', 'request-a', 'donor_authorized', 'donor', 1), 'donor')
        self.p.apply(Event('a', 'request-a', 'activated', 'recipient', 2), 'recipient')
        self.assertEqual(self.p.state, 'ACTIVE')
        self.assertEqual(len(self.p.journal), 3)

    def test_duplicate_does_not_append(self):
        self.p.apply(self.sms, 'recipient')
        self.assertEqual(len(self.p.journal), 1)

    def test_cross_request_rejected(self):
        with self.assertRaises(ValueError):
            self.p.apply(Event('d', 'request-b', 'donor_authorized', 'donor', 1), 'donor')

    def test_spoofed_issuer(self):
        with self.assertRaises(PermissionError):
            self.p.apply(Event('d', 'request-a', 'donor_authorized', 'donor', 1), 'app')

    def test_stale_sequence_rejected(self):
        self.p.apply(Event('d', 'request-a', 'donor_authorized', 'donor', 1), 'donor')
        with self.assertRaises(ValueError):
            self.p.apply(Event('a', 'request-a', 'activated', 'recipient', 1), 'recipient')

    def test_conflicting_duplicate(self):
        with self.assertRaises(ValueError):
            self.p.apply(Event('s', 'request-a', 'activated', 'recipient', 2), 'recipient')

    def test_replay_after_donor_confirmation(self):
        early = Event('a', 'request-a', 'activated', 'recipient', 2)
        with self.assertRaises(ValueError):
            self.p.apply(early, 'recipient')
        self.p.apply(Event('d', 'request-a', 'donor_authorized', 'donor', 1), 'donor')
        self.assertEqual(self.p.apply(early, 'recipient'), 'ACTIVE')


    def test_missing_request_identity_rejected(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                Portability(value)

    def test_invalid_event_identity_preserves_state(self):
        for value in (None, '', '  ', True, 1):
            event = Event(value, 'request-a', 'donor_authorized', 'donor', 1)
            with self.assertRaises(ValueError):
                self.p.apply(event, 'donor')
        self.assertEqual(self.p.state, 'WAIT_DONOR')
        self.assertEqual(len(self.p.journal), 1)

if __name__ == '__main__':
    unittest.main()
