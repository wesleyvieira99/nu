def set_hold(self):
    with self.lock:
        self.resource = replace(self.resource, hold=True,
                                revision=self.resource.revision + 1)

def archive(self, expected, *, inactive, retention_elapsed,
            no_dependencies, restore_verified):
    evidence = (inactive, retention_elapsed,
                no_dependencies, restore_verified)
    if any(type(value) is not bool for value in evidence):
        raise ValueError('evidências devem ser booleanas neste modelo')
    with self.lock:
        current = self.resource
        if expected != current.revision:
            raise ValueError('evidência de revisão antiga')
        if current.hold or not all((inactive, retention_elapsed,
                                   no_dependencies, restore_verified)):
            raise PermissionError('barreiras não satisfeitas')
        if current.archived:
            return current
        self.resource = replace(current, archived=True,
                                revision=current.revision + 1)
        return self.resource