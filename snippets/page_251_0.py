def realized_cost(rows, fp_cents=500, review_cents=100):
    if any(type(x) is not int or x < 0 for x in (fp_cents, review_cents)):
        raise ValueError("costs must be non-negative integer cents")
    totals = {"missed_fraud": 0, "false_positive": 0, "review": 0}
    for action, fraud, amount_cents in rows:
        if type(amount_cents) is not int or amount_cents < 0:
            raise ValueError("amount must be non-negative integer cents")
        if type(fraud) is not bool:
            raise ValueError("fraud label must be boolean")
        if action == "ALLOW" and fraud:
            totals["missed_fraud"] += amount_cents
        elif action == "BLOCK" and not fraud:
            totals["false_positive"] += fp_cents
        elif action in {"REVIEW", "REVIEW_MISSING", "REVIEW_STALE"}:
            totals["review"] += review_cents
        elif action not in {"ALLOW", "BLOCK"}:
            raise ValueError("unknown action")
    totals["total"] = sum(totals.values())
    return totals

rows = [("ALLOW", True, 10000),
        ("BLOCK", False, 10000),
        ("REVIEW", True, 10000)]
assert realized_cost(rows)["total"] == 10600