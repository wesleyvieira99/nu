def ingest(self, event, crash=False):
    payload = json.dumps(event, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    if event['status'] not in {'transit', 'exception', 'delivered'}:
        raise ValueError('status desconhecido')
    if type(event['seq']) is not int or event['seq'] < 1:
        raise ValueError('sequência inválida')
    with self.db:
        # A decisão de versão deve usar a mesma transação da gravação.
        self.db.execute('BEGIN IMMEDIATE')
        old = self.db.execute('SELECT digest FROM events WHERE event_id=?',
                              (event['event_id'],)).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError('evento conflitante')
            return 'duplicate'
        row = self.db.execute('SELECT seq,status FROM shipments '
            'WHERE shipment_id=?', (event['shipment_id'],)).fetchone()
        self.db.execute('INSERT INTO events VALUES (?,?)',
                        (event['event_id'], digest))
        if row and event['seq'] <= row[0]:
            return 'stale'
        if row and row[1] == 'delivered' and event['status'] != 'delivered':
            raise ValueError('regressão terminal')
        self.db.execute('INSERT OR REPLACE INTO shipments VALUES (?,?,?,?)',
            (event['shipment_id'], event['seq'], event['status'],
             event['next_step']))
        if crash:
            raise RuntimeError('falha antes do commit')
    return 'applied'