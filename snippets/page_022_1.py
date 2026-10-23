# Exemplo de adapter com boto3; cliente e tabela são externos.
# Nomes e valores são sintéticos.
def reserve(table, scope, request_key, fingerprint):
    pk = f"IDEMPOTENCY#{scope}#{request_key}"
    return table.put_item(
        Item={
            "pk": pk,
            "fingerprint": fingerprint,
            "status": "reserved",
            "version": 0,
        },
        ConditionExpression="attribute_not_exists(pk)",
    )

# Uma ConditionalCheckFailedException exige consultar
# o registro: replay compatível ou conflito de payload.
# Não converter todo erro em 'já processado'.
# A expiração da chave precisa respeitar a janela de replay.