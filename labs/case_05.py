"""Agenda sintética por data civil: não paga boletos nem usa infraestrutura real."""
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
import unittest


UTC = timezone.utc


def local_instant(day, hour, minute, zone):
    # Política proposta: primeiro instante válido; na dobra, primeiro UTC.
    naive = datetime.combine(day, time(hour, minute))
    for shift in range(181):
        candidate = naive + timedelta(minutes=shift)
        valid = []
        for fold in (0, 1):
            instant = candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            roundtrip = instant.astimezone(zone).replace(tzinfo=None)
            if roundtrip == candidate:
                valid.append(instant)
        if valid:
            return min(valid)
    raise ValueError("no_valid_instant")


class Planner:
    def __init__(self, zone="America/Sao_Paulo"):
        self.zone = ZoneInfo(zone)
        self.bills, self.sent = {}, set()

    def upsert(self, bill_id, due, cents, version, paid=False):
        if type(cents) is not int or cents <= 0:
            raise ValueError("amount")
        if type(version) is not int or version <= 0:
            raise ValueError("positive_integer_version_required")
        old = self.bills.get(bill_id)
        if old and version <= old["version"]:
            return False
        self.bills[bill_id] = dict(due=due, cents=cents, version=version, paid=paid)
        return True

    def upcoming(self):
        return sorted(((key, value) for key, value in self.bills.items()
                       if not value["paid"]), key=lambda pair: (pair[1]["due"], pair[0]))

    def dispatch(self, bill_id, expected_version, now, hour=9, minute=0):
        if now.tzinfo is None:
            raise ValueError("timezone_required")
        bill = self.bills[bill_id]
        if bill["version"] != expected_version or bill["paid"]:
            return "obsolete"
        target = local_instant(bill["due"], hour, minute, self.zone)
        key = (bill_id, expected_version, bill["due"].isoformat())
        if key in self.sent:
            return "duplicate"
        if now < target:
            return "not_due"
        # Não entregar lembrete que ficou preso até outro dia civil.
        if now.astimezone(self.zone).date() != bill["due"]:
            return "expired"
        self.sent.add(key)
        return "sent_locally"


class Tests(unittest.TestCase):
    def setUp(self):
        self.p = Planner()
        self.p.upsert("b", date(2026, 11, 1), 1234, 1)

    def test_orders_across_month_boundaries(self):
        self.p.upsert("a", date(2026, 10, 31), 999, 1)
        self.assertEqual([key for key, _ in self.p.upcoming()], ["a", "b"])

    def test_sao_paulo_preference_is_utc_12(self):
        self.assertEqual(self.p.dispatch("b", 1, datetime(2026, 11, 1, 11, tzinfo=UTC)),
                         "not_due")
        self.assertEqual(self.p.dispatch("b", 1, datetime(2026, 11, 1, 12, tzinfo=UTC)),
                         "sent_locally")

    def test_paid_before_dispatch_suppresses_reminder(self):
        self.p.upsert("b", date(2026, 11, 1), 1234, 2, paid=True)
        self.assertEqual(self.p.dispatch("b", 1, datetime(2026, 11, 1, 12, tzinfo=UTC)),
                         "obsolete")
        self.assertEqual(self.p.upcoming(), [])

    def test_repeated_dispatch_is_deduplicated(self):
        now = datetime(2026, 11, 1, 12, tzinfo=UTC)
        self.assertEqual(self.p.dispatch("b", 1, now), "sent_locally")
        self.assertEqual(self.p.dispatch("b", 1, now), "duplicate")

    def test_delayed_previous_day_notification_expires(self):
        self.assertEqual(self.p.dispatch("b", 1, datetime(2026, 11, 2, 12, tzinfo=UTC)),
                         "expired")

    def test_gap_advances_to_first_valid_minute(self):
        zone = ZoneInfo("Europe/Berlin")
        value = local_instant(date(2026, 3, 29), 2, 30, zone)
        self.assertEqual(value.astimezone(zone).strftime("%H:%M"), "03:00")

    def test_fold_selects_first_occurrence(self):
        zone = ZoneInfo("Europe/Berlin")
        value = local_instant(date(2026, 10, 25), 2, 30, zone)
        self.assertEqual(value, datetime(2026, 10, 25, 0, 30, tzinfo=UTC))

    def test_old_version_and_naive_clock_rejected(self):
        self.assertFalse(self.p.upsert("b", date(2026, 12, 1), 1234, 1))
        with self.assertRaises(ValueError):
            self.p.dispatch("b", 1, datetime(2026, 11, 1, 12))

    def test_invalid_version_cannot_replace_a_bill(self):
        before = dict(self.p.bills["b"])
        for version in (float("nan"), float("inf"), 1.0, True, 0):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.p.upsert("b", date(2026, 12, 1), 999, version)
        self.assertEqual(self.p.bills["b"], before)


if __name__ == "__main__":
    print("LAB SINTÉTICO 05: usa tzdata do sistema; envio somente em memória.")
    unittest.main(verbosity=2)
