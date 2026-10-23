"""Modelo sintético: recuperação por estados, revisão e prazo. Sem biometria real."""
import sqlite3
import tempfile
import unittest
from pathlib import Path


class Recovery:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cases(
                id TEXT PRIMARY KEY, state TEXT NOT NULL, revision INTEGER,
                expires INTEGER, owner TEXT, verifier TEXT, epoch INTEGER)""")

    def open(self, case_id, owner, now, ttl=300):
        if type(now) is not int or type(ttl) is not int or ttl <= 0:
            raise ValueError("ttl")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO cases VALUES(?, 'review', 0, ?, ?, '', 0)",
                       (case_id, now + ttl, owner))

    def read(self, case_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(case_id)
        return dict(zip(("id", "state", "revision", "expires", "owner",
                         "verifier", "epoch"), row))

    def transition(self, case_id, expected, action, actor, now):
        if type(now) is not int or type(expected) is not int:
            raise ValueError("integer_clock_and_revision_required")
        with sqlite3.connect(self.path, isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if row is None:
                raise KeyError(case_id)
            _, state, revision, expires, owner, verifier, epoch = row
            if expected != revision:
                raise ValueError("stale_revision")
            if now >= expires:
                raise ValueError("expired")
            if action == "verify" and state == "review" and actor != owner:
                state, verifier = "verified", actor
            elif (action == "restore" and state == "verified"
                  and actor not in (owner, verifier)):
                state, epoch = "restored", epoch + 1
            else:
                raise ValueError("invalid_transition_or_actor")
            db.execute("UPDATE cases SET state=?, revision=?, verifier=?, epoch=? "
                       "WHERE id=?", (state, revision + 1, verifier, epoch, case_id))
            db.commit()
        return self.read(case_id)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "recovery.db"
        self.store = Recovery(self.path)
        self.store.open("case", "customer", 100)

    def test_restore_requires_two_distinct_reviewers(self):
        verified = self.store.transition("case", 0, "verify", "reviewer-a", 101)
        self.assertEqual(verified["state"], "verified")
        with self.assertRaises(ValueError):
            self.store.transition("case", 1, "restore", "reviewer-a", 102)
        result = self.store.transition("case", 1, "restore", "reviewer-b", 102)
        self.assertEqual((result["state"], result["epoch"]), ("restored", 1))

    def test_owner_cannot_verify(self):
        with self.assertRaises(ValueError):
            self.store.transition("case", 0, "verify", "customer", 101)
        self.assertEqual(self.store.read("case")["revision"], 0)

    def test_expired_case_cannot_restore(self):
        self.store.transition("case", 0, "verify", "a", 101)
        with self.assertRaisesRegex(ValueError, "expired"):
            self.store.transition("case", 1, "restore", "b", 400)

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

    def test_invalid_clock_cannot_bypass_expiry(self):
        for now in (float("nan"), float("inf"), True, "101"):
            with self.subTest(now=now), self.assertRaises(ValueError):
                self.store.transition("case", 0, "verify", "a", now)
        self.assertEqual(self.store.read("case")["revision"], 0)
        self.store.transition("case", 0, "verify", "a", 101)
        with self.assertRaises(ValueError):
            self.store.transition("case", True, "restore", "b", 102)


if __name__ == "__main__":
    print("LAB SINTÉTICO 02: não verifica identidade ou risco real.")
    unittest.main(verbosity=2)
