def configure(self, user, show_values=False, enabled=True):
    if type(show_values) is not bool or type(enabled) is not bool:
        raise ValueError("boolean_preferences_required")
    old = self.preferences.get(user, {"version": 0})
    self.preferences[user] = dict(show_values=show_values, enabled=enabled,
                                  version=old["version"] + 1)

def enqueue(self, event):
    if set(event) != {"id", "user", "version", "kind", "amount_cents"}:
        raise ValueError("schema")
    if (type(event["version"]) is not int or event["version"] != 1
            or event["kind"] not in ("cashback", "income")):
        raise ValueError("unsupported")
    cents = event["amount_cents"]
    if type(cents) is not int or cents < 0:
        raise ValueError("money")
    payload = json.dumps(event, sort_keys=True)
    old = self.events.get(event["id"])
    if old is not None and old != payload:
        raise ValueError("id_conflict")
    self.events[event["id"]] = payload