def test_orders_across_month_boundaries(self):
    self.p.upsert("a", date(2026, 10, 31), 999, 1)
    self.assertEqual([key for key, _ in self.p.upcoming()], ["a", "b"])

def test_paid_before_dispatch_suppresses_reminder(self):
    self.p.upsert("b", date(2026, 11, 1), 1234, 2, paid=True)
    self.assertEqual(self.p.dispatch(
        "b", 1, datetime(2026, 11, 1, 12, tzinfo=UTC)),
                     "obsolete")
    self.assertEqual(self.p.upcoming(), [])

def test_gap_advances_to_first_valid_minute(self):
    zone = ZoneInfo("Europe/Berlin")
    value = local_instant(date(2026, 3, 29), 2, 30, zone)
    self.assertEqual(value.astimezone(zone).strftime("%H:%M"), "03:00")

def test_fold_selects_first_occurrence(self):
    zone = ZoneInfo("Europe/Berlin")
    value = local_instant(date(2026, 10, 25), 2, 30, zone)
    self.assertEqual(value, datetime(2026, 10, 25, 0, 30, tzinfo=UTC))