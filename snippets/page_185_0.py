    def event(self, ident, generation, kind, scope):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty event identity required')
        if type(generation) is not int or generation < 1:
            raise ValueError('positive integer generation required')
        required = {'delivered': 'carrier', 'dispute': 'customer',
                    'activate': 'customer_verified'}
        if kind not in required or required[kind] != scope:
            raise PermissionError('scope mismatch')
        payload = json.dumps([generation, kind, scope])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload FROM events WHERE id=?',
                                  (ident,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError('event conflict')
                return self.state()
            current, carrier, disputed, active = self.state()
            if generation > current:
                raise ValueError('future generation; event not consumed')
            if generation == current:
                if kind == 'delivered':
                    carrier = 'delivered'
                elif kind == 'dispute':
                    disputed, active = 1, 0
                elif kind == 'activate':
                    if disputed:
                        raise ValueError('dispute requires separate resolution')
                    active = 1
                self.db.execute('UPDATE card SET carrier=?,disputed=?,active=? '
                                'WHERE id=1', (carrier, disputed, active))
            self.db.execute('INSERT INTO events VALUES(?,?)', (ident, payload))
        return self.state()