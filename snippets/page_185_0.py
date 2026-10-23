def allocate(self, token, demand):
    with self.lock:
        if token in self.requests:
            if self.requests[token] != demand:
                raise ValueError('token conflitante')
            return False
        if not demand or set(demand) - set(self.limits):
            raise ValueError('recurso desconhecido ou demanda vazia')
        if any(type(v) is not int or v <= 0 for v in demand.values()):
            raise ValueError('demanda inteira positiva obrigatória')
        available = {}
        for resource, limit in self.limits.items():
            pending = sum(x.get(resource, 0)
                          for x in self.allocations.values())
            available[resource] = (limit - self.used[resource]
                - self.reserve_floor[resource] - pending)
        if any(amount > available[key] for key, amount in demand.items()):
            raise RuntimeError('capacidade insuficiente')
        self.allocations[token] = dict(demand)
        self.requests[token] = dict(demand)
        return True