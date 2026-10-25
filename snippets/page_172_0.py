    def append(self, entry):
        if not isinstance(entry.id, str) or not entry.id.strip():
            raise ValueError('nonempty entry identity required')
        if type(entry.cents) is not int or entry.cents <= 0:
            raise ValueError('positive integer cents required')
        if entry.kind not in {'purchase', 'refund', 'payment'}:
            raise ValueError('unknown entry type')
        with self.lock:
            old = self.entries.get(entry.id)
            if old:
                if old != entry:
                    raise ValueError('entry identity conflict')
                return
            if entry.kind == 'refund':
                purchase = self.entries.get(entry.parent)
                if not purchase or purchase.kind != 'purchase':
                    raise ValueError('missing purchase provenance')
                used = sum(e.cents for e in self.entries.values()
                           if e.kind == 'refund' and e.parent == entry.parent)
                if used + entry.cents > purchase.cents:
                    raise ValueError('refund exceeds purchase')
            elif entry.parent:
                raise ValueError('unexpected parent')
            self.entries[entry.id] = entry

    def snapshot(self):
        with self.lock:
            return tuple(self.entries.values())