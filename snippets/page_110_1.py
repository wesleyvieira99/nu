    def verify(self, owner, generation, code, now):
        if owner != self.owner:
            raise PermissionError("recovery scope")
        if type(now) is not int or now < 0 or not isinstance(code, str):
            raise ValueError("invalid request")
        with self.lock:
            current = self.challenge
            if current is None:
                raise ValueError("challenge unavailable")
            issued_generation, digest, issued_at, expiry, attempts = current
            if type(generation) is not int or generation != self.generation:
                raise ValueError("obsolete contact generation")
            if generation != issued_generation or not issued_at <= now < expiry:
                raise ValueError("challenge expired or not yet valid")
            if attempts >= 3:
                raise ValueError("attempt budget exhausted")
            current[4] += 1
            candidate = hashlib.sha256(code.encode()).digest()
            if not hmac.compare_digest(candidate, digest):
                raise PermissionError("invalid code")
            self.verified, self.challenge = True, None
            return True