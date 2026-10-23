def decide(self, device, amount_cents, street_limit_cents, proof, now,
           permission=True):
    if type(permission) is not bool:
        raise ValueError("boolean_permission_required")
    if (type(amount_cents) is not int or amount_cents <= 0
            or type(street_limit_cents) is not int or street_limit_cents < 0):
        raise ValueError("invalid_money")
    reason = "context_missing"
    trusted = False
    if not permission:
        reason = "permission_missing"
    elif proof:
        body = proof["body"]
        expected = hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(expected, proof["signature"])
        valid = valid and body["device"] == device
        valid = valid and body["epoch"] == self.epoch
        valid = valid and body["issued"] <= now < body["expires"]
        valid = valid and body["network"] in self.approved.get(device, set())
        trusted = valid
        reason = "verified_context" if valid else "context_invalid"
    # Contexto apenas decide este desafio; não autoriza pagamento.
    challenge = amount_cents > street_limit_cents and not trusted
    return dict(challenge=challenge, context_trusted=trusted, reason=reason,
                payment_authorized=False)