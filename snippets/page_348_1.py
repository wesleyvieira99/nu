    def commit(self, actor, quote_id, key, now):
        with self.lock:
            for value in (actor, quote_id, key):
                identifier(value)
            if type(now) is not int or now < 0:
                raise ValueError('invalid clock')
            if actor != self.owner:
                raise PermissionError('account scope')
            if not key:
                raise ValueError('idempotency key required')
            if key in self.receipts:
                if self.receipts[key][0] != quote_id:
                    raise ValueError('idempotency conflict')
                return self.receipts[key]
            quote = self.quotes[quote_id]
            capability = (quote.purpose, quote.currency, quote.country)
            if quote.capability_version != self.version:
                raise ValueError('capability changed; start again')
            if capability not in self.allowed or now >= quote.expires_at:
                raise ValueError('not executable')
            if quote.debit_cents > self.balance:
                raise ValueError('insufficient funds')
            if any(r[0] == quote_id for r in self.receipts.values()):
                raise ValueError('quote already consumed')
            self.balance -= quote.debit_cents
            self.foreign[quote.currency] = self.foreign.get(quote.currency, 0) + \
                quote.foreign_minor
            receipt = (quote_id, quote.debit_cents, quote.foreign_minor)
            self.receipts[key] = receipt
            return receipt