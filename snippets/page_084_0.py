# A geração acompanha o recurso desde a solicitação.
def apply(self, key, resource):
    if not self.active or resource.consent_epoch != self.consent_epoch:
        return False
    if type(resource.sequence) is not int or resource.sequence < 0:
        raise ValueError("integer_sequence_required")
    if key not in self.required:
        raise ValueError("unknown_resource")
    if resource.status not in ("complete", "unsupported", "unavailable"):
        raise ValueError("status")
    if resource.status == "complete":
        if type(resource.cents) is not int or resource.cents < 0:
            raise ValueError("amount")
    elif resource.cents is not None:
        raise ValueError("unknown_is_not_zero")
    old = self.resources.get(key)
    if old and resource.sequence <= old.sequence:
        return False
    self.resources[key] = resource
    return True