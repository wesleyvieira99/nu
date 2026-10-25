    def authorize_refund(self, merchant, payment_id, authorization_id):
        with self.lock:
            for value in (merchant, payment_id, authorization_id):
                identifier(value)
            if merchant != self.p.merchant or payment_id != self.p.payment_id:
                raise PermissionError('merchant/payment scope')
            if not authorization_id:
                raise ValueError('authorization required')
            if self.refund_authority not in (None, authorization_id):
                raise ValueError('conflicting authority')
            self.refund_authority = authorization_id

    def refund(self, actor, authorization_id, key):
        with self.lock:
            identifier(authorization_id)
            identifier(key)
            if actor != 'financial-writer':
                raise PermissionError('financial writer required')
            if not key or not authorization_id:
                raise ValueError('identity required')
            if self.refund_authority != authorization_id:
                raise PermissionError('merchant authorization missing')
            if self.credits:
                old_key, receipt = next(iter(self.credits.items()))
                if old_key != key:
                    raise ValueError('payment already refunded')
                return receipt
            receipt = (self.p.payment_id, self.p.cents, authorization_id)
            self.credits[key] = receipt
            self.state = 'REFUNDED'
            return receipt