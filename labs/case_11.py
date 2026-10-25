"""Synthetic statement provenance, not a Nubank statement calculator.

Immutable snapshots model one currency and one statement, without interest,
tax, exchange rates or installment posting rules. The source ledger and user
authorization must be provided by trusted integrations in production.
"""
from dataclasses import dataclass
import threading
import unittest


@dataclass(frozen=True)
class Entry:
    id: str
    kind: str
    cents: int
    parent: str = ''


class Statement:
    def __init__(self):
        self.entries = {}
        self.lock = threading.Lock()

    # BOOK_CORE_BEGIN
    def append(self, entry):
        if not isinstance(entry.id, str) or not entry.id.strip():
            raise ValueError('nonempty entry identity required')
        if type(entry.cents) is not int or entry.cents <= 0:
            raise ValueError('positive integer cents required')
        if entry.kind not in {'purchase', 'refund', 'payment'}:
            raise ValueError('unknown entry type')
        with self.lock:
            old = self.entries.get(entry.id)
            if old:
                if old != entry:
                    raise ValueError('entry identity conflict')
                return
            if entry.kind == 'refund':
                purchase = self.entries.get(entry.parent)
                if not purchase or purchase.kind != 'purchase':
                    raise ValueError('missing purchase provenance')
                used = sum(e.cents for e in self.entries.values()
                           if e.kind == 'refund' and e.parent == entry.parent)
                if used + entry.cents > purchase.cents:
                    raise ValueError('refund exceeds purchase')
            elif entry.parent:
                raise ValueError('unexpected parent')
            self.entries[entry.id] = entry

    def snapshot(self):
        with self.lock:
            return tuple(self.entries.values())
    # BOOK_CORE_END


def explain(snapshot):
    debit = sum(e.cents for e in snapshot if e.kind == 'purchase')
    refund = sum(e.cents for e in snapshot if e.kind == 'refund')
    payment = sum(e.cents for e in snapshot if e.kind == 'payment')
    signed = debit - refund - payment
    return dict(revision=len(snapshot), purchases=debit, refunds=refund,
                payments=payment, amount_due=max(0, signed),
                credit_balance=max(0, -signed))


class StatementTests(unittest.TestCase):
    def setUp(self):
        self.s = Statement()
        self.s.append(Entry('p', 'purchase', 10000))

    # BOOK_TEST_BEGIN
    def test_three_refunds_reduce_exactly_once(self):
        for i, cents in enumerate((3333, 3333, 3334)):
            refund = Entry('r' + str(i), 'refund', cents, 'p')
            self.s.append(refund)
            self.s.append(refund)
        result = explain(self.s.snapshot())
        self.assertEqual(result['refunds'], 10000)
        self.assertEqual(result['amount_due'], 0)
        self.assertEqual(result['revision'], 4)

    def test_old_snapshot_does_not_change_after_new_credit(self):
        old = self.s.snapshot()
        self.s.append(Entry('r', 'refund', 5000, 'p'))
        self.assertEqual(explain(old)['amount_due'], 10000)
        self.assertEqual(explain(self.s.snapshot())['amount_due'], 5000)
    # BOOK_TEST_END

    def test_over_refund_rejected(self):
        self.s.append(Entry('r1', 'refund', 8000, 'p'))
        with self.assertRaises(ValueError):
            self.s.append(Entry('r2', 'refund', 2001, 'p'))

    def test_orphan_refund_rejected_without_mutation(self):
        with self.assertRaises(ValueError):
            self.s.append(Entry('r', 'refund', 100, 'unknown'))
        self.assertEqual(len(self.s.snapshot()), 1)

    def test_conflicting_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.s.append(Entry('p', 'purchase', 10001))

    def test_credit_balance_is_not_negative_amount_due(self):
        self.s.append(Entry('pay', 'payment', 12000))
        r = explain(self.s.snapshot())
        self.assertEqual((r['amount_due'], r['credit_balance']), (0, 2000))

    def test_cents_must_not_be_float_or_bool(self):
        for amount in (1.1, True, 0, -1):
            with self.assertRaises(ValueError):
                self.s.append(Entry('x', 'refund', amount, 'p'))

    def test_concurrent_refunds_cannot_exceed_purchase(self):
        results = []
        def attempt(ident):
            try:
                self.s.append(Entry(ident, 'refund', 6000, 'p'))
                results.append('ok')
            except ValueError:
                results.append('rejected')
        threads = [threading.Thread(target=attempt, args=(str(i),))
                   for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ['ok', 'rejected'])
        self.assertEqual(explain(self.s.snapshot())['refunds'], 6000)

    def test_invalid_identity_does_not_change_snapshot(self):
        for ident in (None, '', ' ', 0):
            with self.assertRaises(ValueError):
                self.s.append(Entry(ident, 'refund', 100, 'p'))
        self.assertEqual(explain(self.s.snapshot())['amount_due'], 10000)


if __name__ == '__main__':
    unittest.main()
