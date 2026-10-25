    def redeem(self, actor, quote_id, choice, key, now):
        with self.lock:
            for value in (actor, quote_id, key):
                identifier(value)
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if actor != self.owner:
                raise PermissionError('account scope')
            if choice != 'cash' or not key:
                raise ValueError('explicit supported choice required')
            command = (quote_id, choice)
            if key in self.receipts:
                old, receipt = self.receipts[key]
                if old != command:
                    raise ValueError('idempotency conflict')
                return receipt
            quote = self.quotes[quote_id]
            if now >= quote.expires_at:
                raise ValueError('quote expired')
            if quote.balance_version != self.version:
                raise ValueError('balance changed; preview again')
            if quote.points_minor > self.points:
                raise ValueError('insufficient points')
            self.points -= quote.points_minor
            self.cash += quote.cash_cents
            self.version += 1
            receipt = (quote_id, quote.points_minor, quote.cash_cents)
            self.receipts[key] = (command, receipt)
            return receipt