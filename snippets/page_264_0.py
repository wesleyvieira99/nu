def contract_id(window_seconds=60, missing="null", unit="cents"):
    contract = {"window": window_seconds, "missing": missing,
                "unit": unit, "bound": "(at-window, at]", "version": 1}
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]


def compare(batch, online, batch_contract, online_contract, tolerance=0):
    validate_comparison(batch, online, tolerance)
    if batch_contract != online_contract:
        return "CONTRACT_MISMATCH"
    if batch is None or online is None:
        return "MATCH_MISSING" if batch is online else "MISSING_MISMATCH"
    if abs(batch - online) > tolerance:
        return "VALUE_MISMATCH"
    return "MATCH"

left = contract_id(60)
right = contract_id(30)
assert compare(0, 0, left, right) == "CONTRACT_MISMATCH"
assert compare(None, 0, left, left) == "MISSING_MISMATCH"