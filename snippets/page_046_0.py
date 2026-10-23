def run_crash_worker(self, fault: str, expected_exit: int):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()),
         "--crash-worker", str(self.database), fault],
        capture_output=True, text=True, timeout=20,
    )
    self.assertEqual(result.returncode, expected_exit, result.stderr)
    self.bank = SyntheticPayments(self.database)

def test_process_crash_before_commit_rolls_back_and_resume_executes_once(self):
    self.run_crash_worker("crash_before_commit", 72)
    self.assert_invariants(balance=1000, payments=0)
    receipt = self.bank.pay(**self.command())
    self.assertEqual(self.bank.pay(**self.command()), receipt)
    self.assert_invariants(balance=300, payments=1)

def test_process_crash_after_commit_preserves_receipt_and_resume_replays(self):
    self.run_crash_worker("crash_after_commit", 73)
    self.assert_invariants(balance=300, payments=1)
    stored = json.loads(self.bank.inspect("alice")["payments"][0]["receipt_json"])
    self.assertEqual(self.bank.pay(**self.command()), stored)
    self.assert_invariants(balance=300, payments=1)