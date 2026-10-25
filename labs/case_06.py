"""Independent dispute evidence model, no card-network or storage integration.
Hashes bind immutable bytes; scan flags are trusted adapter test fixtures, not
an antivirus. Production needs secure upload, actual scanning, retention,
admissibility rules per network and durable owner-scoped transactions.
"""
import hashlib
import threading
import unittest


class Dossier:
    def __init__(self, owner, cutoff):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("nonempty owner identity required")
        if type(cutoff) is not int or cutoff < 0: raise ValueError("cutoff")
        self.owner, self.cutoff = owner, cutoff
        self.items, self.seen = [], {}
        self.lock = threading.Lock()

    # BEGIN CORE
    def append(self, owner, upload_id, content, now):
        if owner != self.owner:
            raise PermissionError("dispute scope")
        if not upload_id or type(content) is not bytes:
            raise ValueError("upload identity and bytes required")
        if not 0 < len(content) <= 1024 * 1024:
            raise ValueError("attachment size")
        if type(now) is not int or now < 0:
            raise ValueError("clock")
        digest = hashlib.sha256(content).hexdigest()
        with self.lock:
            if upload_id in self.seen:
                previous = self.items[self.seen[upload_id]]
                if previous["digest"] != digest:
                    raise ValueError("upload identity conflict")
                return dict(previous)
            item = dict(version=len(self.items) + 1, digest=digest,
                        received_at=now, state="quarantined",
                        late=now >= self.cutoff)
            self.seen[upload_id] = len(self.items)
            self.items.append(item)
            return dict(item)
    # END CORE

    def scan(self, version, clean=False, trusted=False):
        if trusted is not True or type(clean) is not bool:
            raise PermissionError("verified scanner verdict required")
        with self.lock:
            if type(version) is not int or not 1 <= version <= len(self.items):
                raise ValueError("version")
            item = self.items[version - 1]
            if item["state"] != "quarantined": raise ValueError("already scanned")
            item["state"] = "reviewable" if clean else "rejected"

    def submit(self, version, role, admissible=False):
        with self.lock:
            if role != "dispute-analyst": raise PermissionError("analyst scope")
            if type(version) is not int or not 1 <= version <= len(self.items):
                raise ValueError("version")
            item = self.items[version - 1]
            if item["state"] != "reviewable" or item["late"]:
                raise ValueError("not eligible for this submission window")
            if admissible is not True: raise ValueError("admissibility required")
            item["state"] = "submitted"


class DossierTests(unittest.TestCase):
    def setUp(self): self.d = Dossier("a", 100)
    def upload(self, key="u1", data=b"synthetic document", now=50):
        return self.d.append("a", key, data, now)

    # BEGIN TESTS
    def test_late_evidence_is_retained_without_submission_promise(self):
        item = self.upload(now=101)
        self.d.scan(item["version"], True, True)
        with self.assertRaises(ValueError):
            self.d.submit(item["version"], "dispute-analyst", True)
        self.assertEqual(len(self.d.items), 1)
        self.assertEqual(self.d.items[0]["state"], "reviewable")

    def test_reused_upload_id_cannot_replace_evidence(self):
        original = self.upload()
        with self.assertRaises(ValueError):
            self.upload(data=b"replacement")
        self.assertEqual(self.d.items[0]["digest"], original["digest"])
    # END TESTS

    def test_upload_is_not_submission(self):
        self.upload()
        with self.assertRaises(ValueError): self.d.submit(1, "dispute-analyst", True)
    def test_malware_cannot_submit(self):
        self.upload(); self.d.scan(1, False, True)
        with self.assertRaises(ValueError): self.d.submit(1, "dispute-analyst", True)
    def test_owner_scope(self):
        with self.assertRaises(PermissionError): self.d.append("b", "u", b"x", 1)
    def test_duplicate_upload_returns_same_version(self):
        self.assertEqual(self.upload(), self.upload()); self.assertEqual(len(self.d.items), 1)
    def test_return_value_cannot_mutate_record(self):
        item = self.upload(); item["state"] = "submitted"
        self.assertEqual(self.d.items[0]["state"], "quarantined")
    def test_truthy_scanner_rejected(self):
        self.upload()
        with self.assertRaises(PermissionError): self.d.scan(1, True, 1)
    def test_exact_cutoff_is_late(self):
        self.assertTrue(self.upload(now=100)["late"])
    def test_nan_time_rejected(self):
        with self.assertRaises(ValueError): self.upload(now=float("nan"))
    def test_clean_admissible_can_submit(self):
        self.upload(); self.d.scan(1, True, True)
        self.d.submit(1, "dispute-analyst", True)
        self.assertEqual(self.d.items[0]["state"], "submitted")
    def test_empty_content_rejected(self):
        with self.assertRaises(ValueError): self.upload(data=b"")

    def test_invalid_owner_rejected_before_state_exists(self):
        for owner in (None, "", " \t\n", 0, True):
            with self.subTest(owner=owner):
                candidate = Dossier.__new__(Dossier)
                with self.assertRaises(ValueError): candidate.__init__(owner, 100)
                self.assertEqual(vars(candidate), {})

    def test_missing_upload_identity_cannot_add_evidence(self):
        for owner in (None, "", " \t\n"):
            with self.subTest(owner=owner), self.assertRaises(PermissionError):
                self.d.append(owner, "u", b"x", 1)
        self.assertEqual(self.d.items, [])
        self.assertEqual(self.d.seen, {})


if __name__ == '__main__':
    unittest.main()
