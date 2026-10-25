"""Versioned Nu+ campaign model. External proposal, not the bank's policy engine.
Rules are a deliberately bounded illustration of the cited campaign: full
eligibility, custody exceptions and maintenance checks require integration.
Signed custody events, durable transactions and real payment rails are absent.
"""
from dataclasses import dataclass
from datetime import date
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
import unittest

def identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError('nonblank string identity required')
    return value



@dataclass(frozen=True)
class Transfer:
    event_id: str
    owner: str
    settled: date
    signed_cents: int


class Campaign:
    def __init__(self, owner):
        identifier(owner)
        self.owner, self.events, self.paid = owner, {}, {}
        self.rule_version, self.lock = 'nuplus-demo-v1', RLock()
        self.frozen_total = None

    def record(self, event, authenticated_source):
        with self.lock:
            identifier(event.event_id)
            identifier(event.owner)
            if type(event.settled) is not date:
                raise ValueError('invalid settlement date')
            if authenticated_source != 'custody' or event.owner != self.owner:
                raise PermissionError('custody scope')
            if not event.event_id or type(event.signed_cents) is not int:
                raise ValueError('invalid event')
            if event.event_id in self.events and self.events[event.event_id] != event:
                raise ValueError('event identity conflict')
            self.events[event.event_id] = event

    # BOOK CORE START
    def schedule(self, actor, active_subscription):
        with self.lock:
            identifier(actor)
            if actor != self.owner:
                raise PermissionError('account scope')
            if active_subscription is not True:
                return {'state': 'INELIGIBLE', 'total_cents': 0, 'dues': ()}
            net = sum(e.signed_cents for e in self.events.values()
                      if date(2026, 3, 1) <= e.settled <= date(2026, 5, 29))
            total = min(max(net, 0) // 3_000_000 * 18_000, 180_000)
            dues = tuple(date(2026 + (5 + i) // 12, (5 + i) % 12 + 1, 10)
                         for i in range(10)) if total else ()
            return {'state': 'ELIGIBLE' if total else 'BELOW_THRESHOLD',
                    'total_cents': total, 'dues': dues}
    def pay(self, actor, installment, today, balance_maintained=True,
            active_subscription=True):
        with self.lock:
            plan = self.schedule(actor, active_subscription)
            if type(installment) is not int or not 0 <= installment < 10:
                raise ValueError('installment range')
            if installment in self.paid:
                return self.paid[installment]
            if type(today) is not date or not plan['dues']:
                raise ValueError('date or eligibility invalid')
            if today < plan['dues'][installment]:
                raise ValueError('not due')
            if balance_maintained is not True:
                raise ValueError('maintenance review required')
            if self.frozen_total not in (None, plan['total_cents']):
                raise ValueError('plan changed; reconcile')
            self.frozen_total = plan['total_cents']
            self.paid[installment] = self.frozen_total // 10
            return self.paid[installment]
    # BOOK CORE END


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.c = Campaign('owner')
        self.e = Transfer('in', 'owner', date(2026, 5, 29), 3_000_000)
        self.c.record(self.e, 'custody')

    # BOOK TEST START
    def test_complaint_date_is_before_first_due_date(self):
        plan = self.c.schedule('owner', True)
        self.assertEqual(plan['state'], 'ELIGIBLE')
        self.assertEqual(plan['dues'][0], date(2026, 6, 10))
        with self.assertRaises(ValueError):
            self.c.pay('owner', 0, date(2026, 6, 1))
        self.assertEqual(self.c.paid, {})

    def test_outflow_changes_net_eligibility(self):
        out = Transfer('out', 'owner', date(2026, 5, 29), -1)
        self.c.record(out, 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 0)

    def test_concurrent_payment_is_once_per_installment(self):
        def pay(_):
            return self.c.pay('owner', 0, date(2026, 6, 10))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(pay, range(20)))
        self.assertEqual(set(results), {1800})
        self.assertEqual(sum(self.c.paid.values()), 1800)
    # BOOK TEST END

    def test_duplicate_custody_event(self):
        self.c.record(self.e, 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 18_000)

    def test_conflicting_event_rejected(self):
        with self.assertRaises(ValueError):
            self.c.record(Transfer('in', 'owner', self.e.settled, 1), 'custody')

    def test_wrong_owner_and_source(self):
        for event, source in [(self.e, 'app'),
                              (Transfer('x', 'other', self.e.settled, 1), 'custody')]:
            with self.assertRaises(PermissionError):
                self.c.record(event, source)
        with self.assertRaises(PermissionError):
            self.c.schedule('other', True)

    def test_campaign_bounds_and_cap(self):
        self.c.record(Transfer('early', 'owner', date(2026, 2, 28), 90_000_000), 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 18_000)
        self.c.record(Transfer('valid', 'owner', date(2026, 3, 1), 90_000_000), 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 180_000)

    def test_subscription_and_maintenance(self):
        self.assertEqual(self.c.schedule('owner', False)['state'], 'INELIGIBLE')
        with self.assertRaises(ValueError):
            self.c.pay('owner', 0, date(2026, 6, 10), False)
        self.assertEqual(self.c.paid, {})

    def test_inactive_subscription_cannot_create_payment(self):
        with self.assertRaises(ValueError):
            self.c.pay('owner', 0, date(2026, 6, 10), active_subscription=False)
        self.assertEqual(self.c.paid, {})

    def test_late_custody_change_requires_plan_review(self):
        self.c.pay('owner', 0, date(2026, 6, 10))
        self.c.record(Transfer('late', 'owner', self.e.settled, 3_000_000), 'custody')
        with self.assertRaises(ValueError):
            self.c.pay('owner', 1, date(2026, 7, 10))
        self.assertEqual(sum(self.c.paid.values()), 1800)

    def test_reads_and_writes_share_lock(self):
        def action(i):
            self.c.record(Transfer(str(i), 'owner', self.e.settled, 1), 'custody')
            return self.c.schedule('owner', True)['total_cents']
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(set(pool.map(action, range(100))), {18_000})

    def test_final_due_in_march(self):
        self.assertEqual(self.c.schedule('owner', True)['dues'][-1], date(2027, 3, 10))

    def test_negative_net_cannot_create_debt(self):
        self.c.record(Transfer('out', 'owner', self.e.settled, -9_000_000), 'custody')
        self.assertEqual(self.c.schedule('owner', True)['total_cents'], 0)


    def test_missing_owner_rejected_before_state(self):
        for value in (None, '', '  ', True, 1):
            with self.assertRaises(ValueError):
                Campaign(value)

    def test_invalid_transfer_identity_preserves_events(self):
        for value in (None, '', '  ', True, 1):
            event = Transfer(value, 'owner', self.e.settled, 3_000_000)
            with self.assertRaises(ValueError):
                self.c.record(event, 'custody')
        self.assertEqual(len(self.c.events), 1)
        self.assertEqual(self.c.paid, {})

if __name__ == '__main__':
    unittest.main()
