def test_partial_is_not_complete(self):
    self.p.apply("account", self.resource())
    self.assertEqual(self.p.summarize(110),
                     dict(cents=100, complete=False,
                          gaps={"investment": "missing"}))

def test_zero_is_a_real_complete_position(self):
    self.p.apply("account", self.resource())
    self.p.apply("investment", self.resource(0))
    self.assertTrue(self.p.summarize(110)["complete"])

def test_unsupported_requires_none(self):
    with self.assertRaises(ValueError):
        self.p.apply("investment", self.resource(0, status="unsupported"))
    self.p.apply("investment", self.resource(None, status="unsupported"))
    self.assertEqual(self.p.summarize(110)["gaps"]["investment"], "unsupported")

def test_old_or_duplicate_events_do_not_overwrite(self):
    self.p.apply("account", self.resource(200, sequence=2))
    self.assertFalse(self.p.apply("account", self.resource(100)))
    self.assertFalse(self.p.apply("account", self.resource(300, sequence=2)))
    self.assertEqual(self.p.summarize(110)["cents"], 200)