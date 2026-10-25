    def apply(self, ident, amount, plan, crash=False):
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('nonempty payment identity required')
        if type(amount) is not int or amount <= 0:
            raise ValueError('positive integer cents required')
        if any(type(v) is not int or v <= 0 for v in plan.values()):
            raise ValueError('invalid allocation')
        encoded = json.dumps(plan, sort_keys=True)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT amount,plan FROM payments WHERE id=?',
                                  (ident,)).fetchone()
            if old:
                if old != (amount, encoded):
                    raise ValueError('payment conflict')
                return self.receipt(ident)
            if sum(plan.values()) > amount:
                raise ValueError('allocation exceeds received amount')
            for target, value in plan.items():
                changed = self.db.execute('UPDATE obligations SET due=due-? '
                    'WHERE id=? AND due>=?', (value, target, value)).rowcount
                if changed != 1:
                    raise ValueError('unknown or overpaid obligation')
                self.db.execute('INSERT INTO allocations VALUES(?,?,?)',
                                (ident, target, value))
            if crash:
                raise RuntimeError('crash before commit')
            self.db.execute('INSERT INTO payments VALUES(?,?,?,?)',
                            (ident, amount, encoded, amount - sum(plan.values())))
        return self.receipt(ident)