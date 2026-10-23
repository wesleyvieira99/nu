# max_age mede a idade em segundos simulados.
# Uma lacuna não recebe um valor zero substituto.
# A interface deve preservar complete e gaps.
def summarize(self, now, max_age=60):
    total, gaps = 0, {}
    if not self.active:
        return dict(cents=None, complete=False, gaps={"consent": "revoked"})
    for key in sorted(self.required):
        item = self.resources.get(key)
        if item is None:
            gaps[key] = "missing"
        elif item.status != "complete":
            gaps[key] = item.status
        elif not 0 <= now - item.observed_at <= max_age:
            gaps[key] = "stale_or_future"
        else:
            total += item.cents
    return dict(cents=total, complete=not gaps, gaps=gaps)