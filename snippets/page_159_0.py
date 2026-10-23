def export_record(purchase, subject, secret):
    if purchase.owner != subject:
        raise PermissionError('objeto não autorizado')
    if purchase.status not in LABELS:
        raise ValueError('estado desconhecido')
    if type(purchase.amount_cents) is not int or purchase.amount_cents <= 0:
        raise ValueError('centavos inteiros positivos')
    if purchase.revision < 1:
        raise ValueError('revisão inválida')
    body = {
        'kind': 'synthetic-purchase-record',
        'purchase_id': purchase.purchase_id,
        'revision': purchase.revision,
        'amount_cents': purchase.amount_cents,
        'currency': 'BRL',
        'merchant': purchase.merchant,
        'status': purchase.status,
        'label': LABELS[purchase.status],
        'notice': 'Não é recibo fiscal nem prova de quitação da fatura.'
    }
    signature = hmac.new(secret, canonical(body), hashlib.sha256).hexdigest()
    return {'body': body, 'integrity_tag': signature}