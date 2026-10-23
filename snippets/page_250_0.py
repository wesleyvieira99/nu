def toy_score(features):
    validate_features(features)
    amount = min(features.amount_cents / 100000, 4)
    velocity = min(features.velocity, 10)
    z = -4 + 0.5 * amount + 0.7 * velocity
    z += 1.2 * int(features.device_change)
    return 1 / (1 + math.exp(-z))


def decide(features, allow_below=0.30, block_from=0.85):
    if not 0 <= allow_below < block_from <= 1:
        raise ValueError("invalid thresholds")
    if features is None:
        return "REVIEW_MISSING"
    validate_features(features)
    if features.age_seconds > 60:
        return "REVIEW_STALE"
    probability_like = toy_score(features)
    if probability_like >= block_from:
        return "BLOCK"
    if probability_like >= allow_below:
        return "REVIEW"
    return "ALLOW"