def test_stale_revision_cannot_repeat_verification(self):
    self.store.transition("case", 0, "verify", "a", 101)
    with self.assertRaisesRegex(ValueError, "stale_revision"):
        self.store.transition("case", 0, "verify", "b", 102)

def test_reopen_preserves_case_and_epoch(self):
    self.store.transition("case", 0, "verify", "a", 101)
    reopened = Recovery(self.path)
    self.assertEqual(reopened.read("case")["revision"], 1)
    reopened.transition("case", 1, "restore", "b", 102)
    self.assertEqual(Recovery(self.path).read("case")["epoch"], 1)

def test_cannot_skip_review_or_restore_twice(self):
    with self.assertRaises(ValueError):
        self.store.transition("case", 0, "restore", "b", 101)
    self.store.transition("case", 0, "verify", "a", 101)
    self.store.transition("case", 1, "restore", "b", 102)
    with self.assertRaises(ValueError):
        self.store.transition("case", 2, "restore", "c", 103)
    self.assertEqual(self.store.read("case")["epoch"], 1)