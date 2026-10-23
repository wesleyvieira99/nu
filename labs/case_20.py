"""Synthetic assistive journey and semantics contract, not authentication.
Run: python3 work/v2/labs/case_20.py
The proof receipt is a trusted test fixture, not cryptographic verification.
"""
from dataclasses import dataclass, replace
import json
import unittest


@dataclass(frozen=True)
class Session:
    card: str
    stage: str = 'NEW'


MOVES = {
    ('NEW', 'identify'): 'IDENTIFIED',
    ('IDENTIFIED', 'read_instructions'): 'INSTRUCTIONS',
    ('INSTRUCTIONS', 'start_verification'): 'VERIFYING',
    ('VERIFYING', 'camera_unavailable'): 'ASSISTED',
    ('ASSISTED', 'retry_camera'): 'VERIFYING',
}


def advance(session, action):
    target = MOVES.get((session.stage, action))
    if target is None:
        raise ValueError('Transition is not permitted')
    return replace(session, stage=target)


def accept_proof(session, receipt, consumed):
    if session.stage not in ('VERIFYING', 'ASSISTED'):
        raise ValueError('Verification is not expected')
    if receipt.get('verified') is not True or receipt.get('card') != session.card:
        raise ValueError('Proof does not authorize this card')
    if not isinstance(receipt.get('id'), str) or not receipt['id'].strip():
        raise ValueError('Non-empty receipt identifier required')
    if receipt['id'] in consumed:
        raise ValueError('Receipt already consumed')
    consumed.add(receipt['id'])
    return replace(session, stage='VERIFIED')


def activate(session):
    if session.stage != 'VERIFIED':
        raise ValueError('Verified identity required')
    return replace(session, stage='ACTIVE')


@dataclass(frozen=True)
class Element:
    key: str
    label: str
    order: int
    actionable: bool = False


def semantics_errors(elements):
    errors, orders, keys = [], set(), set()
    for item in elements:
        if not item.label.strip():
            errors.append(f'{item.key}:missing_label')
        if item.order in orders:
            errors.append(f'{item.key}:duplicate_order')
        if item.key in keys:
            errors.append(f'{item.key}:duplicate_key')
        orders.add(item.order)
        keys.add(item.key)
    if not any(item.actionable for item in elements):
        errors.append('screen:no_action')
    return errors


def ready():
    session = Session('synthetic-card-A')
    for action in ('identify', 'read_instructions', 'start_verification'):
        session = advance(session, action)
    return session


def proof(card='synthetic-card-A', verified=True, identifier='fixture-1'):
    return {'id': identifier, 'card': card, 'verified': verified}


class JourneyTests(unittest.TestCase):
    def test_camera_path(self):
        self.assertEqual(activate(accept_proof(ready(), proof(), set()))
                         .stage, 'ACTIVE')
    def test_assisted_path(self):
        session = advance(ready(), 'camera_unavailable')
        self.assertEqual(activate(accept_proof(session, proof(), set()))
                         .stage, 'ACTIVE')
    def test_no_proof_no_activation(self):
        with self.assertRaises(ValueError):
            activate(advance(ready(), 'camera_unavailable'))
    def test_unverified_proof(self):
        with self.assertRaises(ValueError):
            accept_proof(ready(), proof(verified=False), set())
    def test_wrong_card(self):
        with self.assertRaises(ValueError):
            accept_proof(ready(), proof(card='other-card'), set())
    def test_replay(self):
        consumed = set()
        accept_proof(ready(), proof(), consumed)
        with self.assertRaises(ValueError):
            accept_proof(ready(), proof(), consumed)
    def test_invalid_transition(self):
        with self.assertRaises(ValueError):
            advance(Session('synthetic-card-A'), 'start_verification')
    def test_retry_preserves_card(self):
        session = advance(ready(), 'camera_unavailable')
        self.assertEqual(advance(session, 'retry_camera'), ready())
    def test_valid_semantics(self):
        self.assertEqual(semantics_errors([
            Element('heading', 'Ativar cartão', 0),
            Element('help', 'Obter ajuda para continuar', 1, True)]), [])
    def test_missing_label(self):
        self.assertIn('help:missing_label', semantics_errors([
            Element('help', '', 0, True)]))
    def test_duplicate_identity_and_order(self):
        errors = semantics_errors([Element('a', 'Um', 0, True),
                                   Element('a', 'Dois', 0)])
        self.assertIn('a:duplicate_order', errors)
        self.assertIn('a:duplicate_key', errors)
    def test_no_available_action(self):
        self.assertIn('screen:no_action', semantics_errors([
            Element('error', 'Câmera indisponível', 0)]))

    def test_verification_requires_exact_true(self):
        for value in ('false', 'true', 1, None):
            consumed = set()
            with self.assertRaises(ValueError):
                accept_proof(ready(), proof(verified=value), consumed)
            self.assertEqual(consumed, set())

    def test_receipt_identifier_is_nonempty(self):
        for value in ('', '   ', None, 42):
            consumed = set()
            with self.assertRaises(ValueError):
                accept_proof(ready(), proof(identifier=value), consumed)
            self.assertEqual(consumed, set())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(JourneyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assisted = advance(ready(), 'camera_unavailable')
    active = activate(accept_proof(assisted, proof(), set()))
    print(json.dumps({'fallback_before_proof': assisted.stage,
                      'after_trusted_test_receipt': active.stage,
                      'semantics_errors': semantics_errors([
                          Element('error', 'Câmera indisponível', 0)])},
                     ensure_ascii=False, indent=2))
    raise SystemExit(not result.wasSuccessful())
