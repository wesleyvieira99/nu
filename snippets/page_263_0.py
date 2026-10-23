def window_sum(events, at, known_at, seconds=60, available=True):
    validate_window(at, known_at, seconds, available)
    if not available:
        return None
    unique = {}
    for event in events:
        values = (event.occurred, event.known, event.amount_cents)
        if any(type(value) is not int for value in values):
            raise ValueError("integer times and cents required")
        if event.known > known_at or event.occurred > at:
            continue
        if not at - seconds < event.occurred <= at:
            continue
        if event.id in unique and unique[event.id] != event:
            raise ValueError("conflicting event")
        unique[event.id] = event
    return sum(event.amount_cents for event in unique.values())

late = [Event("x", 95, 110, 900)]
assert window_sum(late, 100, 100) == 0
assert window_sum(late, 100, 120) == 900