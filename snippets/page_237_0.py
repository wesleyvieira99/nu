def route(scores, available, urgent=False, threshold=0.75, min_weight=4):
    if type(urgent) is not bool:
        raise ValueError("urgent must be boolean")
    if urgent:
        return {"queue": "human_urgent", "reason": "declared_urgency"}
    validate_ranking(scores, threshold, min_weight)
    total = sum(scores.values())
    if total < min_weight:
        return {"queue": "human_general", "reason": "insufficient"}
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    intent, weight = ranked[0]
    confidence = weight / total
    if confidence < threshold or intent not in available:
        return {"queue": "human_general", "reason": "abstention"}
    return {"queue": intent, "reason": "ranked", "share": confidence}

clear = route({"card": 8, "pix": 1}, {"card"})
uncertain = route({"card": 5, "pix": 5}, {"card"})
assert clear["queue"] == "card"
assert uncertain["queue"] == "human_general"
assert route({}, set())["reason"] == "insufficient"
assert route({}, set(), True)["queue"] == "human_urgent"