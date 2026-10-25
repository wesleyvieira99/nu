"""Independent Pix receipt/refund model; no real banking integration.
SQLite serializes local transitions. trusted models an adapter boundary, not
cryptography. Production needs signed events, ledger reconciliation, identity,
retention and an event publisher. Timeouts never create refunds or payments.
"""
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class Receipts:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS ops (
              id TEXT PRIMARY KEY, owner TEXT NOT NULL, amount INTEGER NOT NULL,
              state TEXT NOT NULL, returned INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY, op TEXT NOT NULL, target TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def create(self, op, owner, amount):
        if type(amount) is not int or amount <= 0 or not op or not owner:
            raise ValueError("positive cents and identity required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT owner,amount FROM ops WHERE id=?",
                             (op,)).fetchone()
            if row and row != (owner, amount): raise ValueError("intent conflict")
            db.execute("INSERT OR IGNORE INTO ops VALUES (?,?,?,'pending',0)",
                       (op, owner, amount))

    # BEGIN CORE
    def confirm(self, op, event_id, target, trusted=False):
        if trusted is not True or not event_id:
            raise PermissionError("verified adapter required")
        allowed = {"pending": {"settled", "refund_pending"},
                   "refund_pending": {"refunded"}}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT op,target FROM events WHERE id=?",
                               (event_id,)).fetchone()
            if prior:
                if prior != (op, target):
                    raise ValueError("event identity conflict")
                return False
            row = db.execute("SELECT state,amount FROM ops WHERE id=?",
                             (op,)).fetchone()
            if not row:
                raise KeyError(op)
            if target not in allowed.get(row[0], set()):
                raise ValueError("illegal transition")
            returned = row[1] if target == "refunded" else 0
            db.execute("UPDATE ops SET state=?,returned=? WHERE id=?",
                       (target, returned, op))
            db.execute("INSERT INTO events VALUES (?,?,?)",
                       (event_id, op, target))
            return True
    # END CORE

    def read(self, op, owner):
        with self.connect() as db:
            row = db.execute("SELECT owner,state,amount,returned FROM ops "
                             "WHERE id=?", (op,)).fetchone()
        if not row or row[0] != owner: raise PermissionError("receipt scope")
        return dict(state=row[1], amount_cents=row[2], returned_cents=row[3])


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bank = Receipts(Path(self.tmp.name) / "receipts.db")
        self.bank.create("pix-a", "owner-a", 30000)

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self, event, state):
        return self.bank.confirm("pix-a", event, state, True)

    # BEGIN TESTS
    def test_concurrent_refund_replays_once(self):
        self.apply("failed", "refund_pending")
        barrier = threading.Barrier(4)
        def retry(_):
            barrier.wait(timeout=5)
            return self.apply("refund", "refunded")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(retry, range(4)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(self.bank.read("pix-a", "owner-a")[
            "returned_cents"], 30000)

    def test_timeout_is_not_refund_authority(self):
        for _ in range(10):
            self.bank.read("pix-a", "owner-a")
        receipt = self.bank.read("pix-a", "owner-a")
        self.assertEqual(receipt["state"], "pending")
        self.assertEqual(receipt["returned_cents"], 0)
    # END TESTS

    def test_refund_without_failure_is_rejected(self):
        with self.assertRaises(ValueError): self.apply("e", "refunded")

    def test_settled_cannot_use_failure_refund(self):
        self.apply("paid", "settled")
        with self.assertRaises(ValueError): self.apply("e", "refund_pending")

    def test_untrusted_cannot_change_state(self):
        for value in (False, None, 1, "true"):
            with self.assertRaises(PermissionError):
                self.bank.confirm("pix-a", "x", "settled", value)

    def test_wrong_owner_cannot_read(self):
        with self.assertRaises(PermissionError): self.bank.read("pix-a", "b")

    def test_duplicate_intent_conflicts(self):
        with self.assertRaises(ValueError): self.bank.create("pix-a", "a", 1)

    def test_duplicate_event_payload_conflicts(self):
        self.apply("e", "refund_pending")
        with self.assertRaises(ValueError): self.apply("e", "refunded")

    def test_reopen_preserves_refund(self):
        self.apply("f", "refund_pending"); self.apply("r", "refunded")
        reopened = Receipts(self.bank.path)
        self.assertEqual(reopened.read("pix-a", "owner-a")["state"], "refunded")

    def test_invalid_money_fails(self):
        for value in (True, 0, -1, 1.5, float("nan")):
            with self.assertRaises(ValueError): self.bank.create("b", "a", value)

    def test_unknown_operation_has_no_event(self):
        with self.assertRaises(KeyError):
            self.bank.confirm("missing", "unique", "settled", True)
        self.assertTrue(self.apply("unique", "settled"))

    def test_rejected_transition_rolls_back_event(self):
        with self.assertRaises(ValueError): self.apply("r", "refunded")
        self.apply("f", "refund_pending")
        self.assertTrue(self.apply("r", "refunded"))


if __name__ == '__main__':
    unittest.main()
