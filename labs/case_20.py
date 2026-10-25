"""NuPay-style orphan-order reconciliation model; external, synthetic proposal.
A timeout opens investigation and never creates refund authority. Production
needs signed merchant evidence, card-ledger settlement, durable idempotency,
chargeback policy and tenant-scoped authorization; no real payment is sent.
"""
from dataclasses import dataclass
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
import unittest

def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError('nonblank string identity required')
    return value



@dataclass(frozen=True)
class Payment:
    merchant: str
    payment_id: str
    order_ref: str
    cents: int
    captured_at: int


class Reconciler:
    def __init__(self, payment):
        for value in (payment.merchant, payment.payment_id, payment.order_ref):
            identifier(value)
        if type(payment.captured_at) is not int or payment.captured_at < 0:
            raise ValueError('invalid capture time')
        if type(payment.cents) is not int or payment.cents <= 0:
            raise ValueError('positive integer cents required')
        self.p, self.state = payment, 'CAPTURED_UNACKNOWLEDGED'
        self.refund_authority, self.credits = None, {}
        self.lock = RLock()

    def investigate(self, now, grace=900):
        with self.lock:
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if type(grace) is not int or grace < 0:
                raise ValueError('invalid grace')
            if self.state == 'CAPTURED_UNACKNOWLEDGED' and now - self.p.captured_at >= grace:
                self.state = 'INVESTIGATING'
            return self.state

    def acknowledge_order(self, merchant, order_ref):
        with self.lock:
            identifier(merchant)
            identifier(order_ref)
            if merchant != self.p.merchant or order_ref != self.p.order_ref:
                raise PermissionError('merchant/order scope')
            if self.state == 'REFUNDED' or self.refund_authority:
                raise ValueError('refund conflict; reconcile')
            self.state = 'ORDER_ACKNOWLEDGED'

    # BOOK CORE START
    def authorize_refund(self, merchant, payment_id, authorization_id):
        with self.lock:
            for value in (merchant, payment_id, authorization_id):
                identifier(value)
            if merchant != self.p.merchant or payment_id != self.p.payment_id:
                raise PermissionError('merchant/payment scope')
            if not authorization_id:
                raise ValueError('authorization required')
            if self.refund_authority not in (None, authorization_id):
                raise ValueError('conflicting authority')
            self.refund_authority = authorization_id

    def refund(self, actor, authorization_id, key):
        with self.lock:
            identifier(authorization_id)
            identifier(key)
            if actor != 'financial-writer':
                raise PermissionError('financial writer required')
            if not key or not authorization_id:
                raise ValueError('identity required')
            if self.refund_authority != authorization_id:
                raise PermissionError('merchant authorization missing')
            if self.credits:
                old_key, receipt = next(iter(self.credits.items()))
                if old_key != key:
                    raise ValueError('payment already refunded')
                return receipt
            receipt = (self.p.payment_id, self.p.cents, authorization_id)
            self.credits[key] = receipt
            self.state = 'REFUNDED'
            return receipt
    # BOOK CORE END


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.r = Reconciler(Payment('shop-a', 'payment-a', 'order-a', 5000, 100))

    # BOOK TEST START
    def test_timeout_is_not_refund_authority(self):
        self.assertEqual(self.r.investigate(1000), 'INVESTIGATING')
        with self.assertRaises(PermissionError):
            self.r.refund('financial-writer', 'invented', 'a')
        self.assertEqual(self.r.credits, {})

    def test_cross_merchant_authority_is_rejected(self):
        with self.assertRaises(PermissionError):
            self.r.authorize_refund('shop-b', 'payment-a', 'grant')
        self.assertIsNone(self.r.refund_authority)

    def test_concurrent_refunds_credit_once(self):
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        def refund(_):
            return self.r.refund('financial-writer', 'grant', 'a')
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(refund, range(20)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(sum(v[1] for v in self.r.credits.values()), 5000)
    # BOOK TEST END

    def test_late_order_after_refund_is_not_fulfilled(self):
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        self.r.refund('financial-writer', 'grant', 'a')
        with self.assertRaises(ValueError):
            self.r.acknowledge_order('shop-a', 'order-a')
        self.assertEqual(self.r.state, 'REFUNDED')

    def test_acknowledged_order_can_be_merchant_cancelled(self):
        self.r.acknowledge_order('shop-a', 'order-a')
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        self.r.refund('financial-writer', 'grant', 'a')
        self.assertEqual(self.r.state, 'REFUNDED')

    def test_grace_boundary(self):
        self.assertEqual(self.r.investigate(999), 'CAPTURED_UNACKNOWLEDGED')
        self.assertEqual(self.r.investigate(1000), 'INVESTIGATING')

    def test_wrong_payment_cannot_authorize(self):
        with self.assertRaises(PermissionError):
            self.r.authorize_refund('shop-a', 'other', 'grant')

    def test_customer_cannot_post_credit(self):
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        with self.assertRaises(PermissionError):
            self.r.refund('customer', 'grant', 'a')

    def test_alternative_key_cannot_credit_twice(self):
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        self.r.refund('financial-writer', 'grant', 'a')
        with self.assertRaises(ValueError):
            self.r.refund('financial-writer', 'grant', 'b')

    def test_conflicting_order_identity(self):
        with self.assertRaises(PermissionError):
            self.r.acknowledge_order('shop-a', 'other-order')
        self.assertEqual(self.r.state, 'CAPTURED_UNACKNOWLEDGED')


    def test_invalid_clock_has_no_effect(self):
        for now in (float('nan'), float('inf'), True, -1):
            with self.assertRaises(ValueError):
                self.r.investigate(now)
        self.assertEqual(self.r.state, 'CAPTURED_UNACKNOWLEDGED')

    def test_missing_payment_identity_rejected(self):
        for value in (None, '', '  ', True, 1):
            for field in range(3):
                ids = ['merchant', 'payment', 'order']
                ids[field] = value
                with self.assertRaises(ValueError):
                    Reconciler(Payment(*ids, 100, 0))

    def test_invalid_authorization_and_key_have_no_credit(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                self.r.authorize_refund('shop-a', 'payment-a', value)
        self.assertIsNone(self.r.refund_authority)
        self.r.authorize_refund('shop-a', 'payment-a', 'grant')
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                self.r.refund('financial-writer', 'grant', value)
        self.assertEqual(self.r.credits, {})

if __name__ == '__main__':
    unittest.main()
