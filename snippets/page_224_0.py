def gate(baseline, candidate, telemetry_complete=True, min_n=50):
    if type(min_n) is not int or min_n <= 0:
        raise ValueError("min_n must be positive integer")
    if type(telemetry_complete) is not bool:
        raise ValueError("telemetry_complete must be boolean")
    validate_stats(baseline)
    validate_stats(candidate)
    if not telemetry_complete:
        return "HOLD_TELEMETRY"
    if baseline["n"] < min_n or candidate["n"] < min_n:
        return "HOLD_SAMPLE"
    if candidate["rate"] < baseline["rate"] - 0.03:
        return "PAUSE_SUCCESS"
    if candidate["p95"] > baseline["p95"] * 1.25:
        return "PAUSE_LATENCY"
    return "ELIGIBLE_FOR_REVIEW"

baseline = {"n": 100, "rate": 0.98, "p95": 300}
candidate = {"n": 100, "rate": 0.90, "p95": 300}
assert gate(baseline, candidate) == "PAUSE_SUCCESS"
assert gate(baseline, baseline) == "ELIGIBLE_FOR_REVIEW"
assert gate(baseline, baseline, False) == "HOLD_TELEMETRY"
small = {"n": 10, "rate": 1.0, "p95": 100}
assert gate(baseline, small) == "HOLD_SAMPLE"