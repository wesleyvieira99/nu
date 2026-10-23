# day é uma data civil já validada.
# zone usa regras IANA, não um offset fixo.
# A ida e volta detecta horários inexistentes.
# fold considera as duas ocorrências de uma dobra.
def local_instant(day, hour, minute, zone):
    # Política proposta: primeiro instante válido; na dobra, primeiro UTC.
    naive = datetime.combine(day, time(hour, minute))
    for shift in range(181):
        candidate = naive + timedelta(minutes=shift)
        valid = []
        for fold in (0, 1):
            instant = candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            roundtrip = instant.astimezone(zone).replace(tzinfo=None)
            if roundtrip == candidate:
                valid.append(instant)
        if valid:
            return min(valid)
    raise ValueError("no_valid_instant")