def accept_proof(session, receipt, consumed):
    if session.stage not in ('VERIFYING', 'ASSISTED'):
        raise ValueError('Verification is not expected')
    if receipt.get('verified') is not True or receipt.get('card') != session.card:
        raise ValueError('Proof does not authorize this card')
    if not isinstance(receipt.get('id'), str) or not receipt['id'].strip():
        raise ValueError('Non-empty receipt identifier required')
    if receipt['id'] in consumed:
        raise ValueError('Receipt already consumed')
    consumed.add(receipt['id'])
    return replace(session, stage='VERIFIED')


def activate(session):
    if session.stage != 'VERIFIED':
        raise ValueError('Verified identity required')
    return replace(session, stage='ACTIVE')

session = advance(ready(), 'camera_unavailable')
assert session.stage == 'ASSISTED'
consumed = set()
verified = accept_proof(session, proof(), consumed)
assert verified.stage == 'VERIFIED'
assert activate(verified).stage == 'ACTIVE'
assert 'fixture-1' in consumed