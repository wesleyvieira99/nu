"""Caso 10: registro compartilhável sintético; não é recibo fiscal."""
from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import unittest


@dataclass(frozen=True)
class Purchase:
    purchase_id: str
    owner: str
    revision: int
    amount_cents: int
    merchant: str
    status: str


LABELS = {'pending': 'Autorização pendente',
          'confirmed': 'Registro de compra confirmada',
          'reversed': 'Compra estornada'}


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False).encode()


def export_record(purchase, subject, secret):
    if purchase.owner != subject:
        raise PermissionError('objeto não autorizado')
    if purchase.status not in LABELS:
        raise ValueError('estado desconhecido')
    if type(purchase.amount_cents) is not int or purchase.amount_cents <= 0:
        raise ValueError('centavos inteiros positivos')
    if purchase.revision < 1:
        raise ValueError('revisão inválida')
    body = {
        'kind': 'synthetic-purchase-record',
        'purchase_id': purchase.purchase_id,
        'revision': purchase.revision,
        'amount_cents': purchase.amount_cents,
        'currency': 'BRL',
        'merchant': purchase.merchant,
        'status': purchase.status,
        'label': LABELS[purchase.status],
        'notice': 'Não é recibo fiscal nem prova de quitação da fatura.'
    }
    signature = hmac.new(secret, canonical(body), hashlib.sha256).hexdigest()
    return {'body': body, 'integrity_tag': signature}


def verify(document, secret):
    expected = hmac.new(secret, canonical(document['body']),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(document['integrity_tag'], expected)


class Tests(unittest.TestCase):
    def setUp(self):
        self.purchase = Purchase('demo-p1', 'alice', 1, 700,
                                 'loja sintética', 'pending')
        self.secret = b'local-test-only-not-a-production-key'

    def make(self, **changes):
        return export_record(replace(self.purchase, **changes),
                             'alice', self.secret)

    def test_pending_has_no_paid_claim(self):
        self.assertEqual(self.make()['body']['label'], 'Autorização pendente')

    def test_reversed_has_explicit_status(self):
        doc = self.make(status='reversed', revision=2)
        self.assertEqual(doc['body']['label'], 'Compra estornada')
        self.assertEqual(doc['body']['revision'], 2)

    def test_owner_not_in_shareable_body(self):
        self.assertNotIn('owner', self.make()['body'])
        self.assertNotIn('alice', canonical(self.make()).decode())

    def test_wrong_subject_is_denied(self):
        with self.assertRaises(PermissionError):
            export_record(self.purchase, 'bob', self.secret)

    def test_same_snapshot_same_document(self):
        self.assertEqual(self.make(), self.make())

    def test_tampering_detected(self):
        doc = self.make()
        self.assertTrue(verify(doc, self.secret))
        doc['body']['amount_cents'] = 1
        self.assertFalse(verify(doc, self.secret))

    def test_invalid_amount_rejected(self):
        for amount in (True, 1.5, 0, -1):
            with self.assertRaises(ValueError):
                self.make(amount_cents=amount)


if __name__ == '__main__':
    unittest.main(verbosity=2)
