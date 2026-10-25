    def apply(self, event, authenticated_source):
        with self.lock:
            for value in (event.event_id, event.request_id, event.kind, event.source):
                identifier(value)
            if event.request_id != self.request_id:
                raise ValueError('request scope')
            if event.source != authenticated_source:
                raise PermissionError('untrusted source')
            if self.SOURCES.get(event.kind) != event.source:
                raise PermissionError('event authority')
            if type(event.sequence) is not int or event.sequence < 1:
                raise ValueError('invalid sequence')
            if event.event_id in self.seen:
                if self.seen[event.event_id] != event:
                    raise ValueError('event identity conflict')
                return self.state
            if event.sequence <= self.sequences.get(event.source, 0):
                raise ValueError('out-of-order; reconcile')
            allowed = {'sms_sent': ('REQUESTED',),
                       'donor_authorized': ('WAIT_DONOR',),
                       'activated': ('AUTHORIZED',),
                       'cancelled': ('REQUESTED', 'WAIT_DONOR', 'AUTHORIZED')}
            if self.state not in allowed[event.kind]:
                raise ValueError('invalid transition; reconcile')
            self.state = {'sms_sent': 'WAIT_DONOR', 'donor_authorized':
                          'AUTHORIZED', 'activated': 'ACTIVE',
                          'cancelled': 'CANCELLED'}[event.kind]
            self.seen[event.event_id] = event
            self.sequences[event.source] = event.sequence
            self.journal.append(event)
            return self.state