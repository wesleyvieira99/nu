def pay(self, *, account_id, operation_id, amount_cents,
        payee, recovery_epoch, fault=None):
    # Recorte: validação e payload/digest estão no arquivo completo.
    with self._write() as connection:
        account = connection.execute(
            "SELECT balance_cents, recovery_epoch FROM accounts "
            "WHERE account_id=?", (account_id,)
        ).fetchone()
        if account is None:
            raise UnknownAccount(account_id)
        # A sessão é validada antes inclusive de retornar um recibo já existente.
        if recovery_epoch != account["recovery_epoch"]:
            raise StaleSession("Comando de sessão anterior à recuperação")
        previous = connection.execute(
            "SELECT payload_json, payload_hash, receipt_json "
            "FROM payments WHERE operation_id=?",
            (operation_id,),
        ).fetchone()
        if previous is not None:
            # Compara também o conteúdo canônico, sem depender apenas do hash.
            if (previous["payload_hash"] != digest
                    or previous["payload_json"] != payload):
                raise IdempotencyConflict(
                    "operation_id reutilizado com outro payload")
            return json.loads(previous["receipt_json"])
        if account["balance_cents"] < amount_cents:
            raise InsufficientFunds("Saldo insuficiente no cenário sintético")