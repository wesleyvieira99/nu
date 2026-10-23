# Validar a versão antes de registrar uma entrega.
def dispatch(self, bill_id, expected_version, now, hour=9, minute=0):
    if now.tzinfo is None:
        raise ValueError("timezone_required")
    bill = self.bills[bill_id]
    if bill["version"] != expected_version or bill["paid"]:
        return "obsolete"
    target = local_instant(bill["due"], hour, minute, self.zone)
    key = (bill_id, expected_version, bill["due"].isoformat())
    if key in self.sent:
        return "duplicate"
    if now < target:
        return "not_due"
    # Não entregar lembrete que ficou preso até outro dia civil.
    if now.astimezone(self.zone).date() != bill["due"]:
        return "expired"
    self.sent.add(key)
    return "sent_locally"