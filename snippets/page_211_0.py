def publish(self, manifest):
    validate(manifest)
    previous = self.revisions.get(manifest.revision)
    if previous is not None and previous != manifest:
        raise ValueError('revisão é imutável')
    self.revisions[manifest.revision] = manifest

def activate(self, revision):
    if revision not in self.revisions:
        raise ValueError('revisão não publicada')
    self.active = revision

def select(self, capabilities, protocol, fallback):
    if self.revisions.get(fallback.revision) != fallback:
        raise ValueError('fallback não publicado')
    current = self.revisions.get(self.active)
    compatible = current and current.protocol == protocol
    compatible = compatible and set(current.components) <= capabilities
    if compatible:
        return current
    if (fallback.protocol == protocol
            and set(fallback.components) <= capabilities):
        return fallback
    raise ValueError('nenhuma composição compatível')