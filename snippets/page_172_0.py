def apply(self, component, version, cents, observed_at, now):
    if component not in {'balance', 'limit'}:
        raise ValueError('componente desconhecido')
    if type(cents) is not int or cents < 0:
        raise ValueError('centavos inválidos')
    if type(version) is not int or version < 1:
        raise ValueError('versão inválida')
    if observed_at > now:
        raise ValueError('timestamp futuro')
    candidate = (version, cents, observed_at)
    previous = self.parts.get(component)
    if previous and version < previous[0]:
        return False
    if previous and version == previous[0]:
        if previous != candidate:
            raise ValueError('versão conflitante')
        return False
    self.parts[component] = candidate
    return True