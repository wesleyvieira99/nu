import unittest

def can_release(samples, failures, min_samples=1000):
    if type(samples) is not int or type(failures) is not int:
        raise ValueError("counts must be integers")
    if type(min_samples) is not int or min_samples <= 0:
        raise ValueError("invalid sample policy")
    if not 0 <= failures <= samples:
        raise ValueError("invalid counts")
    if samples < min_samples:
        return False
    return failures / samples <= 0.001

class ReleaseGateTests(unittest.TestCase):
    def test_small_sample_does_not_pass(self):
        self.assertFalse(can_release(50, 0))

    def test_error_budget_is_respected(self):
        self.assertTrue(can_release(2000, 2))
        self.assertFalse(can_release(2000, 3))

    def test_invalid_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            can_release(2000, 2001)